import os
import secrets
import uuid

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
model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()
chat_sessions = {}


def get_chat():
    session_id = session.get("chat_id")
    if not session_id:
        session_id = uuid.uuid4().hex
        session["chat_id"] = session_id

    if session_id not in chat_sessions:
        api_key = os.getenv("GOOGLE_API_KEY", "").strip()
        if not api_key:
            raise ValueError("ยังไม่พบ GOOGLE_API_KEY กรุณาตั้งค่าในไฟล์ .env ก่อน")

        client = genai.Client(api_key=api_key)
        chat_sessions[session_id] = {
            "client": client,
            "chat": client.chats.create(
                model=model_name,
                config=types.GenerateContentConfig(system_instruction=ERU_PERSONALITY),
            ),
            "messages": [],
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
    messages = chat_sessions.get(session_id, {}).get("messages", [])
    return jsonify({"messages": messages})


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
    except Exception:
        app.logger.exception("Gemini request failed")
        return jsonify({"error": "ส่งข้อความไม่สำเร็จ ลองใหม่อีกครั้งนะ"}), 502

    reply = response.text or "(เอรุยังนึกคำตอบไม่ออก ลองถามใหม่สิ)"
    chat_state["messages"].extend(
        [{"role": "user", "text": message}, {"role": "assistant", "text": reply}]
    )
    return jsonify({"reply": reply})


@app.post("/api/reset")
def reset_chat():
    session_id = session.pop("chat_id", None)
    if session_id:
        chat_state = chat_sessions.pop(session_id, None)
        if chat_state:
            chat_state["client"].close()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)