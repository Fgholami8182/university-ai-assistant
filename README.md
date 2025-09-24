# 🎓🤖 University AI Assistant
An AI-powered assistant for answering university academic regulations and policies.

---

## ✨ Overview
This project was developed as my **undergraduate thesis**.  
The goal is to design a simple and user-friendly interface where students can ask questions about university regulations and receive accurate, clear, and referenced answers.

---

## 🛠️ Technologies
- **Python (Flask)** — Backend and API
- **Sentence-BERT (all-MiniLM-L6-v2)** — Semantic search
- **Groq LLM API** — Generating fluent and referenced responses
- **SQLite** — Database for feedback and logs
- **HTML + Tailwind CSS + JavaScript** — Frontend UI
- **Waitress + Nginx** — Deployment and serving

---

## 📸 Screenshots
(Add some UI screenshots and Q&A examples here)

---

## ⚙️ Installation & Usage
1. Clone the repository:
   ```bash
   git clone https://github.com/username/university-ai-assistant.git
   cd university-ai-assistant

Create a virtual environment and install dependencies:

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt


Set environment variables (.env file):

GROQ_API_KEY_1=your_key_here
GROQ_API_KEY_2=your_key_here
DB_PATH=./app_data.db
LOG_DIR=./logs


Run the application:

python app.py


Open in browser:

http://localhost:5000

📂 Project Structure
.
├── app.py                # Main Flask app
├── static/               # CSS and JS files
├── templates/            # HTML templates
├── myDataset.json        # Academic regulations dataset
├── requirements.txt      # Python dependencies
├── README.md             # Project documentation
└── .gitignore            # Ignored files

✅ Features

Semantic search for retrieving regulation texts

Natural and referenced answers using LLM

Shows regulation paragraph as source

Simple and user-friendly interface

Feedback mechanism for users

Rate limiter to prevent spam

📌 Limitations

Dependent on the regulation dataset (needs updates)

Requires stable internet for Groq API

Limited support for non-Persian languages (current version)

🚀 Future Improvements

Use of local Persian language models

Multi-language support

Advanced search features

Improved accessibility and UI design

👨‍🏫 Supervisor & Reviewer

Supervisor: [Supervisor Name]

Reviewer: [Reviewer Name]
