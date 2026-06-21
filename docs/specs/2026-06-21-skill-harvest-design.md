# skill-harvest — ดีไซน์

> สรุปทูตอเรียล YouTube เป็น "การ์ดความรู้" ภาษาไทยแบบ interactive (HTML) เก็บสะสมเป็นคลังส่วนตัว
> เน้นทูตอเรียลสายทักษะ เช่น pixel-art animation (Aseprite), การปั้น 3D ฯลฯ

วันที่: 2026-06-21
สถานะ: อนุมัติดีไซน์แล้ว (รวมหมวดหมู่ ข้อ 10) — รอวางแผน implement

---

## 1. เป้าหมาย

ใส่ลิงก์ YouTube → ได้การ์ดความรู้ที่สรุปด้วย AI:
- เน้น **ความรู้ที่เอาไปใช้ทำได้จริง** (เครื่องมือ, ขั้นตอนเรียงลำดับ, ทริค/ค่าตัวเลข, ศัพท์เทคนิค) ไม่ใช่แค่ย่อความ
- สะสมหลายคลิปเป็น **คลังที่ค้น/กรองได้**
- อ่านบน **มือถือ** ได้สบาย (ผู้ใช้ทำงานบนมือถือเป็นหลัก)

### Non-goals (เฟสนี้)
- ไม่ทำ vision/แคปเฟรม (ยกไปเฟส 2)
- ไม่ทำเว็บเซิร์ฟเวอร์/ฐานข้อมูล — เป็น CLI + ไฟล์ในโฟลเดอร์
- ไม่รวมเข้ากับแอป `novel` — เป็นโปรเจกต์แยก

---

## 2. สแต็ก & สภาพแวดล้อม

- **Python CLI** (เครื่องมือหลักของงานนี้อยู่ในระบบนิเวศ Python: `yt-dlp`, `faster-whisper`, `ffmpeg`)
- รัน **ในเครื่องที่มี GPU** → ถอดเสียง Whisper ฟรี ไม่เสียค่า API
- LLM ผ่าน **endpoint แบบ OpenAI-compatible** ตั้งค่าได้: LM Studio ในเครื่อง (ฟรี) / DeepSeek / OpenRouter
- ผลลัพธ์ภาษาไทย

---

## 3. Pipeline

```
ลิงก์ YouTube
   │
   ▼
[1] fetch        yt-dlp → metadata (title, channel, duration, chapters) + ลอง caption
   │
   ▼
[2] transcript   มี caption? ใช้เลย : ดึงเสียง → faster-whisper → transcript + timestamp
   │
   ▼
[3] summarize    LLM → JSON ตาม schema (เครื่องมือ/ขั้นตอน/ทริค/ศัพท์) + map-reduce ถ้ายาว
   │
   ▼
[4] store        เขียน cards/<id>.json (ตัวจริง) + regenerate cards-data.js → gallery.html ใช้ได้
```

---

## 4. โครงสร้างไฟล์

```
skill-harvest/
  cli.py               # entrypoint: รับลิงก์/อาร์กิวเมนต์ (รวม --category override) ต่อท่อทั้งหมด
  fetch.py             # yt-dlp wrapper → metadata + caption (ถ้ามี)
  transcribe.py        # faster-whisper → transcript + timestamp
  summarize.py         # เรียก LLM → โครงสร้าง JSON (validate ตาม schema)
  store.py             # เขียน cards/*.json + regenerate cards-data.js
  config.py            # endpoint, โมเดล, ภาษา, โฟลเดอร์เก็บ, Whisper model size, CATEGORIES (ข้อ 10)
  templates/
    gallery.html       # หน้าแกลลารี (css/js ในตัว, โหลด cards-data.js)
  cards/               # ผลลัพธ์: <id>.json ต่อคลิป (source of truth)
  cards-data.js        # generated: window.CARDS = [...] (ฝังข้อมูลทุกการ์ด)
  gallery.html         # generated/คัดลอกจาก template — เปิดอ่านคลัง
  cache/               # transcript ที่ถอดแล้ว (กันถอดซ้ำเวลา re-run)
  docs/specs/
  requirements.txt
  README.md
```

แต่ละโมดูลมีหน้าที่เดียว สื่อสารผ่าน data structure ชัดเจน เทสต์แยกได้:
- `fetch.py` → คืน `VideoMeta` (+ caption ถ้ามี)
- `transcribe.py` → คืน `Transcript` (segments + ข้อความรวม)
- `summarize.py` → คืน `Card` (dict ตาม schema ข้อ 6)
- `store.py` → เขียนไฟล์ + regenerate ข้อมูล gallery

---

## 5. รูปแบบ output (HTML/JSON)

ตัดสินใจ: **JSON เป็น source of truth + หน้าแกลลารีเดียว**

- `cards/<id>.json` = ข้อมูลโครงสร้างของแต่ละคลิป (แก้/รีเรนเดอร์ใหม่ได้ง่าย, machine-friendly)
- `gallery.html` = หน้าเดียวแสดงทุกการ์ด: ชิปกรองหมวด (ข้อ 10.3), ค้น, กรองด้วย tag, ปุ่มพับ/กางขั้นตอน, ลิงก์กระโดดไปนาทีในคลิป (`youtu.be/<id>?t=<sec>`)

### จุดเทคนิคสำคัญ — เปิดบนมือถือได้โดยไม่ต้องมีเซิร์ฟเวอร์
เปิด `gallery.html` ผ่าน `file://` แล้วใช้ `fetch()` อ่าน `cards/*.json` จะถูกเบราว์เซอร์บล็อกด้วย CORS (โดยเฉพาะบนมือถือ)

**วิธีแก้:** ตอน harvest ทุกครั้ง `store.py` จะ **ฝังข้อมูลการ์ดทั้งหมดเป็นไฟล์ `cards-data.js`** รูปแบบ `window.CARDS = [ ... ];` แล้ว `gallery.html` โหลดผ่าน `<script src="cards-data.js">` (ไม่ใช่ `fetch`) → เปิดไฟล์เดียวบนมือถือใช้ได้ทันที ออฟไลน์ได้ ไม่ต้องรันเซิร์ฟเวอร์

`cards/*.json` ยังเป็น source of truth — `cards-data.js` เป็นแค่ผลรวมที่ regenerate จากมันได้เสมอ

---

## 6. Schema ของการ์ด (JSON)

```jsonc
{
  "id": "yt_<videoId>",
  "title": "Smooth Pixel Attack Animation (Aseprite)",
  "source_url": "https://youtu.be/<videoId>",
  "channel": "...",
  "duration_sec": 754,
  "category": "pixel-art",            // หมวดใหญ่ 1 หมวด/การ์ด (id จาก config ข้อ 10)
  "category_source": "ai",           // "ai" = LLM เดา | "manual" = คนระบุผ่าน --category
  "tags": ["aseprite", "smear", "animation"],   // tag ย่อย (กรองละเอียดใน gallery)
  "harvested_at": "2026-06-21",
  "transcript_source": "caption" | "whisper",
  "summary": "เทคนิคทำแอนิเมชันโจมตีให้ลื่นด้วย smear frames ...",
  "tools": ["Aseprite", "brush 1px", ...],
  "steps": [
    { "text": "ตั้ง keyframe ท่าเริ่ม–ท่าจบก่อน", "t_sec": 42 },
    { "text": "แทรก smear frame 1–2 เฟรมระหว่างกลาง", "t_sec": 90 }
  ],
  "tips": ["อย่าใส่ smear เกิน 2 เฟรม จะดูเบลอ", ...],
  "glossary": [{ "term": "smear frame", "meaning": "..." }],
  "visual_gap": true   // ธง: บางขั้นตอนน่าจะเป็นภาพล้วน รอเฟส 2 เติม
}
```

`t_sec` ใช้ทำลิงก์กระโดดไปนาทีในคลิป (มีเฉพาะเมื่อ transcript มี timestamp)

`category` / `category_source` — รายละเอียดการกำหนดหมวดอยู่ในข้อ 10

---

## 7. Error handling

| กรณี | พฤติกรรม |
|---|---|
| ไม่มี caption + ถอดเสียงพัง | error ชัดเจน **ไม่สร้างการ์ดเปล่า** |
| transcript ยาวเกิน context | แบ่ง chunk → สรุปทีละส่วน → รวม (map-reduce) |
| LLM ตอบไม่ตรง schema | retry; ถ้ายังพัง validate แล้ว fail ชัด ไม่เขียนการ์ดเสีย |
| คลิปที่ความรู้อยู่บนภาพล้วน | ตั้ง `visual_gap: true` + แสดงป้ายเตือนใน gallery (รอเฟส 2) |
| re-run คลิปเดิม | ใช้ transcript จาก `cache/` ไม่ถอดซ้ำ |
| AI เลือกหมวดนอก list | fallback เป็น `category: "other"` ไม่ fail (ดูข้อ 10) |
| `--category <id>` ที่ไม่มีใน config | error ชัดเจน ไม่สร้างการ์ด (กันสะกดผิด) |

---

## 8. Testing

แต่ละโมดูลเทสต์อิสระ:
- `fetch` / `transcribe` — mock subprocess (yt-dlp/whisper) ตรวจการ parse output
- `summarize` — ใช้ transcript ตัวอย่างคงที่ + mock LLM client → ตรวจว่า map-reduce + validate schema ถูก; **ตรวจว่า `category` ที่ได้อยู่ใน config เสมอ และหลุด list → fallback `other`**
- `cli` (หมวด) — `--category <id>` ทับค่า AI + ตั้ง `category_source: "manual"` ถูก; reject id ที่ไม่มีใน config
- `store` — เทสต์ว่าเขียน `cards/*.json` ถูก และ regenerate `cards-data.js` (`window.CARDS=[...]`) ครบทุกการ์ด
- `card render` — สโม๊คเทสต์ว่า gallery.html โหลด cards-data.js ได้ (อย่างน้อยตรวจ template มี `<script src>` ชี้ถูก); **ชิปหมวดครบตาม config + กรองหมวด∧tag ร่วมกันถูก**

---

## 9. การแบ่งเฟส

**เฟส 1 (ทำก่อน):** ครบเส้น caption/Whisper → JSON → gallery ใช้งานจริงกับคลิปที่พูดเยอะ และเป็นโครงให้เฟส 2 ต่อยอด

**เฟส 2 (ทีหลัง):** เพิ่ม `frames.py` แคปเฟรมเป็นระยะ (ffmpeg) → ส่ง vision model อ่านสิ่งบนจอ → เติม `steps`/`tools` ที่ขาด และเคลียร์ `visual_gap` เฉพาะคลิปสายภาพ
```

---

## 10. หมวดหมู่ (Categories)

แต่ละการ์ดมี **1 หมวดใหญ่** (`category`) คนละชั้นกับ `tags` ย่อย — หมวดไว้แยกสายความรู้ (pixel art / 3D / Unity / เรียนญี่ปุ่น / อื่น ๆ), tag ไว้กรองละเอียดในหมวด

### 10.1 รายชื่อหมวด — ลิสต์เดียวใน `config.py`
```python
CATEGORIES = [
    {"id": "pixel-art", "label": "Pixel Art"},
    {"id": "3d",        "label": "3D / โมเดล"},
    {"id": "unity",     "label": "Unity"},
    {"id": "japanese",  "label": "เรียนญี่ปุ่น"},
    {"id": "other",     "label": "อื่น ๆ"},   # fallback เสมอ — ห้ามลบ
]
```
แก้/เพิ่มหมวดที่เดียวจบ → ทั้ง AI (prompt) และ gallery (ชิป) เห็นหมวดใหม่ทันที โดยไม่แตะโค้ดอื่น

### 10.2 การกำหนดหมวด — AI เดา + override ได้
- **AI เดา:** `summarize.py` ส่ง id หมวดทั้งหมดจาก config เข้า prompt → LLM ต้องเลือก `category` จาก id ที่มี**เท่านั้น** → validate; ถ้า LLM ตอบ id นอก list → fallback `"other"` → `category_source: "ai"`
- **คน override:** `cli.py` รับ `--category <id>` → ทับค่า AI, ตั้ง `category_source: "manual"`; ถ้า `<id>` ไม่อยู่ใน config → error ชัดเจน ไม่สร้างการ์ด (กันสะกดผิด)

### 10.3 การแสดงผลใน gallery
- **แถบชิปหมวดด้านบนสุด:** `[ทั้งหมด] [Pixel Art] [3D] [Unity] [ญี่ปุ่น] [อื่นๆ]` — กดเลือกได้ทีละหมวด, โชว์จำนวนการ์ดต่อหมวด
- ใต้ลงมา: ช่องค้น + ชิป tag ย่อย (เดิม) → ทำงาน **AND** กับหมวดที่เลือก (เช่น หมวด pixel-art + tag "smear")
- การ์ดแต่ละใบโชว์ป้ายหมวดมุมหนึ่ง
- หน้าตา/สไตล์ของ gallery มอบให้ Claude ออกแบบเอง — ข้อบังคับคือ: ใช้ดีบนมือถือ (ผู้ใช้หลักอยู่มือถือ) และเปิด `file://` ออฟไลน์ได้ (ข้อมูลฝังใน `cards-data.js` ตามข้อ 5)
