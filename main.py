import os
import secrets
import sqlite3
import uuid
from contextlib import contextmanager

from flask import Flask, jsonify, render_template, request, session
from dotenv import load_dotenv
from google import genai
from google.genai import types


ERU_PERSONALITY = """
คุณคือ Suzune Eru (ซูซูเนะ เอรุ) AI VTuber สายแสบซน ร่าเริง และกวนประสาท
พูดตรง จี้จุดเก่ง ใช้สรรพนามอย่าง แก, ฉัน, นาย และใช้ภาษาไทยวัยรุ่นแบบเป็นธรรมชาติ
แซวได้เจ็บนิดๆ แต่ให้เป็นมุกขำๆ ไม่เหยียด ไม่คุกคาม และไม่ทำร้ายกันจริงจัง
หัวเราะด้วย 555 ได้ตามจังหวะ อย่าพูดสุภาพแข็งๆ แบบบอททั่วไป
"""


load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
chat_sessions = {}
chat_db_path = os.getenv("CHAT_DB_PATH", os.path.join(app.instance_path, "chat_history.sqlite3"))


@contextmanager
def connect_db():
    os.makedirs(os.path.dirname(os.path.abspath(chat_db_path)), exist_ok=True)
    database = sqlite3.connect(chat_db_path, timeout=10)
    try:
        yield database
        database.commit()
    except Exception:
        database.rollback()
        raise
    finally:
        database.close()


def init_db():
    with connect_db() as database:
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL
            )
            """
        )
        database.execute(
            "CREATE INDEX IF NOT EXISTS messages_by_session ON messages(session_id, id)"
        )


def load_messages(session_id):
    with connect_db() as database:
        rows = database.execute(
            "SELECT role, text FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    return [{"role": role, "text": text} for role, text in rows]


def save_messages(session_id, messages):
    with connect_db() as database:
        database.executemany(
            "INSERT INTO messages (session_id, role, text) VALUES (?, ?, ?)",
            [(session_id, message["role"], message["text"]) for message in messages],
        )


def delete_messages(session_id):
    with connect_db() as database:
        database.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))


init_db()


def get_chat():
    session_id = session.get("chat_id")
    if not session_id:
        session_id = uuid.uuid4().hex
        session["chat_id"] = session_id

    if session_id not in chat_sessions:
        api_key = os.getenv("GOOGLE_API_KEY", "").strip()
        if not api_key:
            raise ValueError("ยังไม่พบ GOOGLE_API_KEY กรุณาตั้งค่าในไฟล์ .env ก่อน")

        messages = load_messages(session_id)
        history = [
            types.Content(
                role="user" if message["role"] == "user" else "model",
                parts=[types.Part.from_text(text=message["text"])],
            )
            for message in messages
        ]
        client = genai.Client(api_key=api_key)
        chat_sessions[session_id] = {
            "session_id": session_id,
            "client": client,
            "chat": client.chats.create(
                model=model_name,
                config=types.GenerateContentConfig(system_instruction=ERU_PERSONALITY),
                history=history,
            ),
            "messages": messages,
        }
    return chat_sessions[session_id]


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def status():
    return jsonify({"configured": bool(os.getenv("GOOGLE_API_KEY", "").strip())})


@app.get("/api/history")
def history():
    session_id = session.get("chat_id")
    return jsonify({"messages": load_messages(session_id) if session_id else []})


@app.post("/api/chat")
def send_message():
    message = request.json.get("message", "").strip() if request.is_json else ""
    if not message:
        return jsonify({"error": "พิมพ์ข้อความก่อนส่งสิ"}), 400

    try:
        chat_state = get_chat()
        response = chat_state["chat"].send_message(message)
    except ValueError as error:
        return jsonify({"error": str(error)}), 503
    except Exception as error:
        if getattr(error, "code", None) == 503:
            app.logger.warning("Gemini is temporarily unavailable")
            return jsonify({"error": "Gemini กำลังมีผู้ใช้เยอะ ลองส่งข้อความอีกครั้งในอีกสักครู่นะ"}), 503
        app.logger.exception("Gemini request failed")
        return jsonify({"error": "ส่งข้อความไม่สำเร็จ ลองใหม่อีกครั้งนะ"}), 502

    reply = response.text or "(เอรุยังนึกคำตอบไม่ออก ลองถามใหม่สิ)"
    new_messages = [
        {"role": "user", "text": message},
        {"role": "assistant", "text": reply},
    ]
    save_messages(chat_state["session_id"], new_messages)
    chat_state["messages"].extend(new_messages)
    return jsonify({"reply": reply})


@app.post("/api/reset")
def reset_chat():
    session_id = session.pop("chat_id", None)
    if session_id:
        delete_messages(session_id)
        chat_state = chat_sessions.pop(session_id, None)
        if chat_state:
            chat_state["client"].close()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)