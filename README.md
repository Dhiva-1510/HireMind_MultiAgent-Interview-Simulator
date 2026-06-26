# Hire MIND AI 🧠

![Hire MIND AI Banner](https://img.shields.io/badge/Status-Active-brightgreen) ![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-00a393) ![React](https://img.shields.io/badge/React-18.2-61dafb) ![MongoDB](https://img.shields.io/badge/MongoDB-4.4%2B-47A248)

**Hire MIND AI** is an advanced, autonomous Multi-Agent AI Interview Simulator designed to provide candidates with highly realistic, dynamic, and corporate-specific interview experiences. By leveraging Large Language Models (LLMs), real-time Voice Synthesis, and a robust microservices architecture, the platform automatically parses resumes, tailors questions to specific domains, evaluates answers in real-time, and generates personalized, actionable feedback reports.

---

## ✨ Key Features

- **Automated Resume Parsing:** Extracts skills, target roles, and experience from PDF/DOCX files using a multi-strategy approach (PyPDF, Docx2Txt, Llama-Index) powered by LLM structuring.
- **Dynamic Multi-Agent System:**
  - **Question Agent:** Dynamically formulates non-repetitive questions tailored to the candidate's domain and target role, mapped to real-world MNC standards (e.g., Google, Amazon, Zoho).
  - **Evaluation Agent:** Assesses candidate responses (both text and transcribed voice) in real-time, scoring for Relevance, Depth, Accuracy, and Communication.
  - **Feedback Agent:** Acts as a senior mentor, generating a multi-paragraph, professional feedback letter upon interview completion.
- **Voice Integration:** Built-in Text-to-Speech (TTS) for AI questions and Speech-to-Text (STT) for candidate answers to simulate live verbal interviews.
- **Skill Mismatch Detection:** Intelligently cross-references the candidate's answers with their claimed resume skills to flag discrepancies.
- **Personalized Resource Recommendation:** Automatically fetches curated learning materials (e.g., YouTube tutorials) tailored exactly to the candidate's identified weak areas.
- **Ethereal Email Reporting:** Automatically generates and dispatches beautiful HTML performance reports to candidates upon completion via Node.js integration.

---

## 🏗️ Architecture & Tech Stack

**Backend Engine:**
*   **Framework:** FastAPI (Python)
*   **LLM Provider:** Groq API (`llama-3.3-70b-versatile`) for lightning-fast agentic workflows.
*   **Databases:** 
    *   **Vector DB:** ChromaDB (for storing and retrieving chunked resume data).
    *   **App DB:** MongoDB (with an automatic JSON fallback for localized offline persistence).

**Frontend UI:**
*   **Framework:** React (Vite) styled with modern, dark-themed enterprise SaaS aesthetics. 
*   **Serving:** Bundled and served as static files directly via the FastAPI backend.

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend and email reporting)
- MongoDB (running locally on port `27017` or configured via URI)
- Groq API Key

### 1. Clone the Repository
```bash
git clone https://github.com/Dhiva-1510/HireMind_MultiAgent-Interview-Simulator.git
cd HireMind_MultiAgent-Interview-Simulator
```

### 2. Backend Setup
```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Environment Variables
Create a `.env` file in the root directory and add your keys:
```env
GROQ_API_KEY=your_groq_api_key_here
MONGODB_URI=mongodb://localhost:27017/
```

### 5. Run the Application
```bash
python app.py
```
*The server will automatically rebuild frontend assets if needed and launch on `http://127.0.0.1:7860`.*

---

## 🔄 Project Workflow

1. **Authentication:** Secure user registration and login.
2. **Setup:** The candidate uploads their resume and configures the interview (selecting the number of Aptitude, Technical, Communication, and Resume-specific questions).
3. **Live Session:** 
   - The AI asks contextual questions via voice.
   - The candidate replies using their microphone or text.
   - The system tracks topics to ensure zero overlap.
4. **Debrief:** The AI finalizes the session, generating scores, a mentorship letter, and recommended learning resources.
5. **Delivery:** The final report is saved to the dashboard and emailed to the candidate.

---

## 🛡️ Security & Resiliency
- **Auto-Cleanup:** Uploaded documents and temporary audio files are strictly deleted from the server immediately after processing.
- **Graceful DB Degradation:** If the primary MongoDB instance is unreachable, the system automatically falls back to a localized file-based I/O (`db_fallback.json`) without interrupting the interview flow.

---

## 🤝 Contributing
Contributions are always welcome! Feel free to open an issue or submit a Pull Request.

---

*Built with ❤️ for next-generation interview preparation.*
