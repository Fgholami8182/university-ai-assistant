from flask import Flask, render_template, request, jsonify
import os, json, sqlite3, logging
from datetime import datetime
from sentence_transformers import SentenceTransformer, util
from groq import Groq
from dotenv import load_dotenv
from waitress import serve
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from logging.handlers import RotatingFileHandler

# ---------- Load Env ----------
load_dotenv()
GROQ_API_KEY_1 = os.getenv("GROQ_API_KEY_1")
GROQ_API_KEY_2 = os.getenv("GROQ_API_KEY_2")
RULES_LINK = os.getenv("RULES_LINK", "#")
DB_PATH = os.getenv("DB_PATH", "app_data.db")
LOG_DIR = os.getenv("LOG_DIR", "logs")
FEEDBACK_FILE = os.getenv("FEEDBACK_FILE", "feedbacks.txt")
os.makedirs(LOG_DIR, exist_ok=True)

# ---------- Logging ----------
logger = logging.getLogger("univ_assistant")
logger.setLevel(logging.INFO)
file_handler = RotatingFileHandler(os.path.join(LOG_DIR, "app.log"), maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.info("شروع سرویس دستیار آیین‌نامه‌ای")

# ---------- Database init ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            feedback TEXT,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS api_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            endpoint TEXT,
            payload TEXT,
            response TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def save_feedback_to_db(name, feedback):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO feedbacks (name, feedback, created_at) VALUES (?, ?, ?)",
              (name, feedback, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    logger.info(f"بازخورد ذخیره شد: نام={name}")

def save_feedback_to_file(name, feedback):
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.utcnow().isoformat()}] {name or 'کاربر ناشناس'}: {feedback}\n")

def save_api_log(ip, endpoint, payload, response_text):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO api_logs (ip, endpoint, payload, response, created_at) VALUES (?, ?, ?, ?, ?)",
                  (ip, endpoint, json.dumps(payload, ensure_ascii=False), response_text[:2000], datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.exception("خطا در ذخیره لاگ API")

# ---------- Groq clients ----------
client_groq1 = Groq(api_key=GROQ_API_KEY_1) if GROQ_API_KEY_1 else None
client_groq2 = Groq(api_key=GROQ_API_KEY_2) if GROQ_API_KEY_2 else None

app = Flask(__name__)

# ---------- Rate Limiter ----------
limiter = Limiter(key_func=get_remote_address, default_limits=[])
limiter.init_app(app)

# ---------- Load Dataset ----------
with open("myDataset.json", "r", encoding="utf-8") as f:
    university_rules = json.load(f)

# ---------- Sentence Transformer ----------
model = SentenceTransformer('all-MiniLM-L6-v2')
rules_embeddings = []
for section, rules in university_rules.items():
    for rule in rules:
        emb = model.encode(rule)
        rules_embeddings.append({"section": section, "rule": rule, "embedding": emb})

# ---------- Relevant Sections ----------
def get_relevant_sections(user_question, threshold=0.45):
    q_emb = model.encode(user_question)
    relevant_sections = set()
    for item in rules_embeddings:
        score = util.cos_sim(q_emb, item["embedding"]).item()
        if score >= threshold:
            relevant_sections.add(item["section"])
    relevant_text = ""
    for sec in relevant_sections:
        full_text = "\n".join(university_rules[sec])
        relevant_text += f"\n\n### {sec}\n{full_text}"
    return relevant_text

# ---------- Build Prompt ----------
def build_prompt(user_question):
    all_rules_text = get_relevant_sections(user_question)
    return f"""
تو یک دستیار دانشگاهی هوشمند هستی. نقشت اینه که با زبان دوستانه، شفاف و ساده، آیین‌نامه‌ها و قوانین آموزشی رو برای دانشجو توضیح بدی.
محدودیت مهم:
- فقط از متن قوانین مرتبط استفاده کن.
- اگر در قوانین پاسخی وجود نداشت، بگو: «در قوانین موجود پاسخی برای این سوال نیست.»
- نظر شخصی اضافه نکن.

### سوال دانشجو:
{user_question}

### قوانین موجود:
{all_rules_text}

خروجی مطلوب:
1. اول: اشاره مستقیم به قوانین.
2. دوم: توضیح روان و قابل فهم.
3. سوم: اگر پاسخی وجود نداشت، بگو «در قوانین نیست.»
"""

# ---------- Groq ----------
def ask_groq1(user_question):
    if not client_groq1:
        logger.warning("Groq1 کلید ندارد")
        return None
    try:
        chat_completion = client_groq1.chat.completions.create(
            messages=[
                {"role": "system", "content": build_prompt(user_question)},
                {"role": "user", "content": user_question}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=500
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.exception("[Groq1] Error")
        return None

def ask_groq2(user_question):
    if not client_groq2:
        logger.warning("Groq2 کلید ندارد")
        return None
    try:
        chat_completion = client_groq2.chat.completions.create(
            messages=[
                {"role": "system", "content": build_prompt(user_question)},
                {"role": "user", "content": user_question}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=500
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.exception("[Groq2] Error")
        return None

def ask_ai(user_question):
    for func in [ask_groq1, ask_groq2]:
        try:
            answer = func(user_question)
        except Exception as e:
            logger.exception("خطا در فراخوانی سرویس")
            answer = None
        if answer:
            return answer
    return "⚠️ خطا: هیچ پاسخی از سرویس‌ها دریافت نشد."

# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
@limiter.limit("1 per 5 seconds")
def ask():
    user_question = request.json.get("question")
    ip = request.remote_addr
    logger.info(f"/ask from {ip}: {user_question}")
    answer = ask_ai(user_question)
    save_api_log(ip, "/ask", {"question": user_question}, answer)
    return jsonify({"answer": answer})

@app.route("/feedback", methods=["POST"])
def feedback():
    data = request.json or {}
    name = (data.get("name") or "").strip()
    fb = (data.get("feedback") or "").strip()
    ip = request.remote_addr
    if not fb:
        logger.info(f"/feedback از {ip} ناموفق - متن خالی")
        return jsonify({"success": False, "message": "متن بازخورد نمی‌تواند خالی باشد."}), 400
    try:
        save_feedback_to_db(name, fb)
        save_feedback_to_file(name, fb)
    except Exception as e:
        logger.exception("خطا در ذخیره بازخورد")
    msg = "بازخورد با موفقیت ثبت شد."
    save_api_log(ip, "/feedback", {"name": name, "feedback": fb}, msg)
    logger.info(f"بازخورد از {ip} ثبت شد: {name}")
    return jsonify({"success": True, "message": msg}), 200

# ---------- Run Server ----------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    serve(app, host="0.0.0.0", port=port)
