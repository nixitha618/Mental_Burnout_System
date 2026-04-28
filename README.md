# 🧠 MindGuard AI – Mental Burnout Detection System

An AI-powered web application that detects early signs of mental burnout using machine learning and provides personalized recommendations through LLM-based guidance, voice interaction, and automated email alerts.

---

## 🚀 Features

* 🔍 **Burnout Prediction Model**
  Predicts burnout risk (Low / Medium / High) using behavioral and lifestyle inputs.

* 🤖 **AI Guidance Chatbot (LLM + RAG)**
  Context-aware chatbot powered by LLM (Llama/Groq) with Retrieval-Augmented Generation for personalized mental wellness advice.

* 🎙️ **Voice Agent Integration**
  Enables real-time, interactive voice-based assistance.

* 📧 **Automated Email Alerts (SMTP)**
  Sends weekly reports and instant alerts for high burnout risk.

* 📊 **Insights & Analytics Dashboard**
  Tracks user trends, patterns, and mental health indicators.

* 🗂️ **History Tracking**
  Stores user assessments for long-term analysis.

---

## 🛠️ Tech Stack

### 🔹 Backend

* Python, FastAPI
* REST API Architecture

### 🔹 Machine Learning

* Scikit-learn (Burnout Prediction Model)

### 🔹 AI / GenAI

* LLM (Llama / Groq API)
* RAG Pipeline (Retrieval-Augmented Generation)
* ChromaDB (Vector Database for semantic retrieval)

### 🔹 Frontend

* HTML, CSS, JavaScript

### Database

* SQLite

### 🔹 Other Integrations

* SMTP (Email Notification System)
* LocalStorage (Session Management)

---

## ⚙️ System Architecture

1. User inputs behavioral data (sleep, stress, workload, etc.)
2. ML model predicts burnout risk
3. Results stored and displayed on dashboard
4. RAG pipeline retrieves context → LLM generates recommendations
5. Email alerts triggered for high-risk users
6. Voice agent enables interactive guidance

---

## 📂 Project Structure

```bash
MindGuard-AI/
│
├── data/
│   ├── raw/
│   │   └── sample_user_data.csv
│   ├── processed/
│   │   └── training_data.csv
│   └── subscriptions.json
│
├── frontend/
│   ├── css/
│   │   └── style.css
│   ├── pages/
│   │   ├── index.html
│   │   ├── login.html
│   │   ├── signup.html
│   │   ├── dashboard.html
│   │   ├── about.html
│   │   └── voice.html
│   └── folder/
│
├── notebooks/
│   ├── 01_eda_and_visualization.ipynb
│   └── 02_model_training_comparison.ipynb
│
├── scripts/
│   └── ingest_knowledge.py
│
├── src/
│   ├── api/
│   │   ├── main.py
│   │   ├── routes.py
│   │   ├── schemas.py
│   │   ├── voice_routes.py
│   │   └── send_otp_endpoint.py
│   │
│   ├── config/
│   │   ├── settings.py
│   │   └── email_config.py
│   │
│   ├── data_pipeline/
│   │   └── preprocessor.py
│   │
│   ├── database/
│   │   ├── models.py
│   │   └── operations.py
│   │
│   ├── ml/
│   │   ├── trainer.py
│   │   ├── predictor.py
│   │   └── explainer.py
│   │
│   ├── rag/
│   │   ├── retriever.py
│   │   ├── generator.py
│   │   └── knowledge_base.py
│   │
│   ├── services/
│   │   ├── email_service.py
│   │   └── scheduler.py
│   │
│   ├── utils/
│   │   ├── helpers.py
│   │   └── logger.py
│   │
│   └── __init__.py
│
├── templates/
│   └── emails/
│       ├── high_risk_alert.html
│       └── weekly_report.html
│
├── tests/
│   ├── test_api.py
│   └── test_ml.py
│
├── fix_chroma_sqlite.py
├── voice_logs.txt
├── requirements.txt
├── requirements2.txt
├── .gitignore
└── README.md
```

---

## ▶️ Getting Started

### 1. Clone Repository

```bash
git clone https://github.com/your-username/mindguard-ai.git
cd mindguard-ai
```

### 2. Setup Backend

```bash
cd src/api
pip install -r ../../requirements.txt
uvicorn main:app --reload
```

### 3. Run Frontend

Open `frontend/pages/index.html` in your browser or use Live Server.

---

## 📌 API Endpoints (Sample)

* `POST /predict` → Burnout prediction
* `POST /explain` → Model explanation
* `POST /guidance` → AI chatbot
* `POST /send/alert` → Email alerts

---

## 🎯 Future Improvements

* 📱 Mobile application integration
* 🧠 Advanced deep learning models
* 📊 Real-time monitoring using wearable data
* 🔐 JWT-based authentication system

---

## 👩‍💻 Author

**Unta Nixitha**
📧 [nixitha51@gmail.com](mailto:nixitha51@gmail.com)
🔗 https://github.com/nixitha618

🔗 Project repository link: https://github.com/nixitha618/Mental_Burnout_System

---

## ⭐ Support

If you like this project, give it a ⭐ on GitHub!
