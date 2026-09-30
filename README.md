# Suzune Eru Chat

เว็บแชตภาษาไทยกับ Suzune Eru ที่ใช้ Gemini API ประวัติแชตแยกตาม browser session และบันทึกใน SQLite

## ติดตั้งและเริ่มใช้งาน (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

เปิดไฟล์ `.env` แล้วใส่ `GOOGLE_API_KEY` จากนั้นเริ่มเว็บ:

```powershell
.\.venv\Scripts\python.exe main.py
```

เปิดเว็บเบราว์เซอร์ที่ <http://127.0.0.1:5000>

กำหนดชื่อโมเดลได้ด้วย `GEMINI_MODEL` ใน `.env` ส่วน `PORT` ใช้เปลี่ยนพอร์ตเริ่มต้นได้ ฐานข้อมูลอยู่ที่ `instance/chat_history.sqlite3` และเปลี่ยนตำแหน่งได้ด้วย `CHAT_DB_PATH`

## นำขึ้นออนไลน์ด้วย Render

1. สร้าง Git repository แล้ว push โปรเจกต์นี้ขึ้น GitHub โดยไฟล์ `.env` ถูกกันออกจาก Git ด้วย `.gitignore`
2. ใน Render เลือก **New > Blueprint** แล้วเชื่อมต่อ GitHub repository นี้
3. ตอน Render ขอค่า `GOOGLE_API_KEY` ให้กรอก API key ในหน้า dashboard ของ Render เท่านั้น ส่วน `FLASK_SECRET_KEY` จะถูกสร้างให้อัตโนมัติ
4. เมื่อ deploy สำเร็จ Render จะแสดง public URL ของเว็บ

การตั้งค่า deploy อยู่ใน `render.yaml` และใช้ Gunicorn เป็น production server ไฟล์ SQLite อยู่บน ephemeral filesystem ของ Render Free จึงอาจหายเมื่อ deploy ใหม่หรือ instance ถูกแทนที่; หากต้องเก็บถาวรต้องใช้ persistent disk หรือฐานข้อมูลภายนอก แพ็กเกจ Free อาจพักการทำงานเมื่อไม่มีผู้เข้าใช้