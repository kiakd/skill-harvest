# skill-harvest

สรุปทูตอเรียล YouTube เป็น "การ์ดความรู้" ภาษาไทยแบบ interactive เก็บเป็นคลังส่วนตัว
เน้นความรู้ที่เอาไปใช้ทำได้จริง (เครื่องมือ / ขั้นตอน / ทริค / ศัพท์) ไม่ใช่แค่ย่อความ

## ติดตั้ง

```bash
pip install -r requirements.txt
# ต้องมี ffmpeg ในเครื่อง (ใช้ตอนถอดเสียงคลิปที่ไม่มี caption)
```

## ตั้งค่า LLM (OpenAI-compatible)

ตั้ง env ตามปลายทางที่ใช้ (ดีฟอลต์ = LM Studio ในเครื่อง):

```bash
export SH_LLM_BASE_URL=http://localhost:1234/v1
export SH_LLM_MODEL=local-model
export SH_LLM_API_KEY=not-needed
```

Windows PowerShell:

```powershell
$env:SH_LLM_BASE_URL = "http://localhost:1234/v1"
$env:SH_LLM_MODEL = "local-model"
$env:SH_LLM_API_KEY = "not-needed"
```

## ใช้งาน

```bash
python cli.py "https://youtu.be/<id>"                # AI เดาหมวดให้
python cli.py "https://youtu.be/<id>" --category 3d  # กำหนดหมวดเอง (override)
```

เปิด `gallery.html` เพื่ออ่านคลัง — เปิดไฟล์ตรง ๆ บนมือถือได้ ไม่ต้องรันเซิร์ฟเวอร์

## หมวดหมู่

แต่ละการ์ดมี 1 หมวดใหญ่ (`category`) + tag ย่อย หลายอัน
แก้รายชื่อหมวดได้ที่ `CATEGORIES` ใน `config.py` ที่เดียว — ทั้ง AI และ gallery เห็นพร้อมกัน

| ขั้นตอน | ไฟล์ |
|---|---|
| fetch metadata + caption | `fetch.py` |
| ถอดเสียง (caption ก่อน, ไม่มีค่อย Whisper) | `transcribe.py` |
| สรุปเป็นการ์ด + เลือกหมวด | `summarize.py` |
| เขียน `cards/*.json` + regen `cards-data.js` | `store.py` |

## เทสต์

```bash
python -m pytest -q
```
