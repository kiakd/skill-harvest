# skill-harvest

สรุปทูตอเรียล YouTube เป็น "การ์ดความรู้" ภาษาไทยแบบ interactive เก็บเป็นคลังส่วนตัว
เน้นความรู้ที่เอาไปใช้ทำได้จริง (เครื่องมือ / ขั้นตอน / ทริค / ศัพท์) ไม่ใช่แค่ย่อความ

## ติดตั้ง

```bash
pip install -r requirements.txt
# ต้องมี ffmpeg ในเครื่อง (ใช้ตอนถอดเสียงคลิปที่ไม่มี caption)
```

## ตั้งค่า LLM (OpenAI-compatible)

ดีฟอลต์ = **Gemma 4 (E4B) ในเครื่องผ่าน Ollama** ตั้งค่าผ่านไฟล์ `.env` (ก็อปจาก `.env.example`)
แอปโหลด `.env` ให้อัตโนมัติ และ `.env` ถูก gitignore ไว้ → ใส่ API key ได้ปลอดภัย ไม่หลุดขึ้น repo

```bash
cp .env.example .env   # แล้วแก้ค่าใน .env
```

**ทางเลือก A — Gemma 4 ในเครื่อง (ฟรี, ออฟไลน์):**
```bash
ollama pull gemma4:e4b      # ดาวน์โหลด ~9.6GB (ต้อง Ollama 0.22+)
# .env:
#   SH_LLM_BASE_URL=http://localhost:11434/v1
#   SH_LLM_MODEL=gemma4:e4b
#   SH_LLM_API_KEY=ollama
```

**ทางเลือก B — DeepSeek (คลาวด์, ต้องมี key):**
```bash
# .env:
#   SH_LLM_BASE_URL=https://api.deepseek.com/v1
#   SH_LLM_MODEL=deepseek-chat
#   SH_LLM_API_KEY=sk-...
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
