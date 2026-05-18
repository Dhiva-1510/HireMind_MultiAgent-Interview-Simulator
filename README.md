---
title: HireMind AI Simulator
emoji: 🧠
colorFrom: green
colorTo: blue
sdk: gradio
app_file: app.py
pinned: false
---

# 🧠 HireMind AI Interview Simulator

HireMind is an advanced, fully-autonomous AI Interview Simulator designed to mimic a real technical interview. It uses LLMs to parse your resume, dynamically generate technical, aptitude, and communication questions, evaluate your responses, and generate actionable feedback and learning resources.

## 🌟 Features
- **Local Gradio UI**: Clean, synchronous interface for a seamless interview experience.
- **Dynamic Question Routing**: Configurable rounds for Aptitude, Technical, Communication, and Resume Deep-Dive.
- **RAG & Memory**: Uses ChromaDB for intelligent local memory tracking and resume contextualization.
- **Voice Fallbacks**: Includes TTS engine integrations to speak interview questions aloud!
- **Resource AI**: Automatically scrapes SerpApi & Tavily to find learning courses for any weak areas identified during the interview.

## 🚀 How to Run

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your API Keys**:
   Create a `.env` file in the root folder with the following:
   ```env
   GROQ_API_KEY=your_key_here
   TAVILY_API_KEY=your_key_here
   SERPAPI_KEY=your_key_here
   ```

3. **Install FFmpeg** (Required for Voice Playback):
   If you are on Windows, simply run:
   ```powershell
   winget install "FFmpeg (Essentials Build)"
   ```

4. **Launch the Simulator**:
   ```bash
   python app.py
   ```
   Open `http://127.0.0.1:7860` in your browser.

## 🏗️ Architecture
- **Gradio**: Web Interface
- **Groq API**: Lightning-fast LLM Inference (Llama 3.3 70B)
- **LlamaIndex**: Robust Resume Parsing
- **ChromaDB**: Local Vector Storage
