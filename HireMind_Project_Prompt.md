# HireMind — Multi-Agent AI Interview Simulator
### Cursor / Kiro AI IDE Prompt — Full Project Specification

> **Purpose:** This document is the single source of truth for building HireMind end-to-end.
> Paste it as your project context in Cursor (`Ctrl+Shift+P → Add to Context`) or Kiro (`/project-spec`).
> Every section is actionable. Follow the architecture, file structure, and workflow exactly.

---

---

## 1. Project Overview

**HireMind** is a multi-agent AI-powered interview simulator that:

- Accepts a candidate's **resume (PDF/DOCX)** as the starting point
- **Parses and profiles** the resume using an LLM extraction pipeline
- Runs a **real-time voice interview** where an AI interviewer asks resume-tailored questions
- **Evaluates answers** in real-time using structured scoring
- **Generates personalised feedback** identifying skill gaps vs. resume claims
- **Delivers curated learning resources** (YouTube videos, articles) via Twilio SMS/WhatsApp
- Stores everything in a **hybrid memory system** (Redis for session state, Chroma for vector search)

### Core Value Proposition

> Unlike generic mock interview tools, HireMind reads the candidate's actual resume and asks questions that probe the *specific* claims they made — then scores whether their verbal answers match what they wrote.

---

## 2. Tech Stack & API Keys

### LLM & AI Services

| Role | Model | Provider | API Key Placeholder |
|------|-------|----------|-------------------|
| Interview Agent | Llama-3.3-70B-Versatile | Groq | `GROQ_API_KEY` |
| Evaluation Agent | gpt oss 120b | groq | `GROQ_API_KEY` |
| Feedback Agent | Qwen/Qwen2.5-32B-Instruct | OpenRouter | `OPENROUTER_API_KEY` |
| Resource agent | serp api|

### Voice

| Role | Service | API Key Placeholder |
|------|---------|-------------------|
| Speech-to-Text | Whisper Large V3 Turbo (Groq) | `GROQ_API_KEY` |
| Text-to-Speech | ElevenLabs | `ELEVENLABS_API_KEY` |
| TTS Fallback | Canopy Labs | `CANOPY_API_KEY` 

### Search & Resources

| Role | Service | API Key Placeholder |
|------|---------|-------------------|
| Web search | SerpAPI | `SERPAPI_KEY` |
| YouTube resources | YouTube Data API v3 | `YOUTUBE_API_KEY` |

### Messaging

| Role | Service | API Key Placeholder |
|------|---------|-------------------|
| SMS / WhatsApp | Twilio | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` |

### Orchestration

| Role | Technology |
|------|-----------|
| Agent orchestration | LangGraph (Python) |
| Backend API | FastAPI |
| Task queue | Celery + Redis |


---

## 3. frontend - gradio

---

## 4. Architecture Deep-Dive

### High-Level Data Flow

```
[Candidate] 
    │
    ▼
[Resume Upload (PDF/DOCX)]
    │
    ▼
[Resume Parser] ─── lamaindex
    │
    ▼
[Resume Extractor] ─── GPT-4.1-mini ──► CandidateProfile JSON
    │              (skills, experience, projects, target_role)
    │
    ├──► [Chroma] ── embed + store profile chunks
    │
    ▼
[LangGraph Orchestrator]
    │
    ├──► [Interview Agent] ─── Llama 70B / Groq
    │         │  (reads CandidateProfile from chromadb)
    │         │  (generates context-aware question)
    │         ▼
    │    [TTS — ElevenLabs] ──► audio stream to candidate
    │
    │    [Candidate speaks answer]
    │         │
    │         ▼
    │    [STT — Whisper V3 Turbo / Groq] ──► transcript
    │         │
    │         ▼
    ├──► [Evaluation Agent] ─── GPT-4.1 structured output
    │         │  (scores: relevance, depth, accuracy vs resume)
    │         │  (detects weak areas)
    │         │
    │         ├──► updates chroma session state
    │         └──► triggers Resource Agent if weak area found
    │
    ├──► [Resource Agent]
    │         │  SerpAPI ──► top articles
    │         │  YouTube API ──► tutorial videos
    │         └──► stores resources in Redis for delivery
    │
    ├──► [Feedback Agent] ─── Qwen 32B / OpenRouter
    │         │  (synthesises all scores + weak areas)
    │         │  (generates personalised improvement plan)
    │         └──► final FeedbackReport JSON
    │
    └──► [Twilio Sender]
              │  SMS: resource links + revision Q&A
              └──► WhatsApp: full report PDF link

---

## 5. Agent Definitions

### 5.1 Interview Agent


**Model:** `llama-3.3-70b-versatile` via Groq API (ultra-low latency, ~200ms)

**System Prompt Template:**
```
You are HireMind, an expert technical interviewer. 

Candidate Profile:
- Name: {candidate_name}
- Target Role: {target_role}
- Skills claimed: {skills}
- Experience: {experience_summary}
- Notable projects: {projects}

Interview Configuration:
- Round: {current_round} of {total_rounds}
- Focus area this round: {focus_area}
- Questions asked so far: {questions_asked}
- Weak areas detected: {weak_areas}

Rules:
1. Ask ONE question at a time. Never ask two questions in one message.
2. Base questions on the candidate's actual resume — reference specific claims.
3. If the candidate mentioned a technology, probe their depth on it.
4. If the evaluation agent flagged a weak area, ask a follow-up question on that area.
5. Vary question types: conceptual, behavioural (STAR), technical problem-solving.
6. Keep questions concise — max 2 sentences.
7. Do NOT give hints or answers. Do NOT evaluate the answer yourself.
8. After {total_rounds} questions, output exactly: "INTERVIEW_COMPLETE"
```


---

### 5.2 Evaluation Agent

**Model:** `gpt oss 120b` via OpenAI (structured output enforced)

**Structured Output Schema:**
```python
from pydantic import BaseModel
from typing import List, Literal

class EvaluationResult(BaseModel):
    question: str
    answer: str
    scores: dict  # {relevance: 1-10, depth: 1-10, accuracy: 1-10, communication: 1-10}
    overall_score: float  # 0.0 - 10.0
    weak_areas: List[str]  # e.g. ["async Python", "system design"]
    strong_areas: List[str]
    resume_mismatch: bool  # True if answer contradicts resume claim
    resume_mismatch_detail: str | None
    follow_up_recommended: bool
    follow_up_topic: str | None
```

**System Prompt:**
```
You are a strict technical interview evaluator. 

Evaluate the candidate's answer against:
1. The question asked
2. Their resume claims: {resume_claims}
3. Expected knowledge level for role: {target_role}

Be objective. Score each dimension 1-10.
Flag resume_mismatch=True if the answer reveals they cannot back up a resume claim.
Identify weak_areas as specific technical topics (not vague like "could improve").
```

*

---

### 5.3 Feedback Agent


**Model:** `Qwen/Qwen2.5-32B-Instruct` via OpenRouter

**Trigger:** Called once after `INTERVIEW_COMPLETE`

**System Prompt:**
```
You are a career coach generating a post-interview feedback report.

Candidate: {candidate_name} | Target Role: {target_role}
Resume Skills: {skills}

Interview Summary:
- Total questions: {total_questions}
- Average score: {avg_score}/10
- All weak areas detected: {all_weak_areas}
- All strong areas: {all_strong_areas}
- Resume mismatches: {resume_mismatches}

Generate a structured, actionable feedback report with:
1. Executive summary (3 sentences)
2. Strengths (bullet points, specific)
3. Gaps vs resume claims (specific, not generic)
4. Top 3 priority areas to improve
5. Suggested 2-week study plan
6. Encouragement note

Be direct, constructive, and specific. Reference actual answers where relevant.
```

---

### 5.4 Resource Agent


**Runs asynchronously via Celery — never blocks the interview loop.**

**Logic:**
```python
from serpapi import GoogleSearch
from googleapiclient.discovery import build

```

---

## 6. Complete Workflow — Step by Step

### Step 1 — Candidate lands on homepage
- Frontend: `app/page.tsx`
- UI shows: "Upload your resume to start your AI interview"
- Accepts `.pdf` and `.docx`
- On upload: `POST /resume/upload` → returns `session_id`

### Step 2 — Resume parsed and profile extracted
- See Section 7 for full detail
- Result: `CandidateProfile` JSON stored in Redis at key `session:{session_id}:profile`
- Profile also embedded and stored in Chroma collection `candidates`

### Step 3 — Interview session initialised
- `POST /session` with `{ session_id, phone_number }`
- Redis key `session:{session_id}:state` created with initial `AgentState`
- Frontend redirects to `/interview/{session_id}`

### Step 4 — WebSocket connection opened
- `WS /ws/interview/{session_id}`
- On connect: server fetches profile from Redis, initialises LangGraph graph
- First node executed: `interview_agent` → generates first question

### Step 5 — TTS converts question to audio
- `tts.py` calls ElevenLabs API with `voice_id = ELEVENLABS_VOICE_ID`
- Returns audio stream → sent over WebSocket as binary frames
- Frontend `VoiceRecorder.tsx` plays audio automatically

### Step 6 — Candidate answers
- After TTS finishes playing, frontend activates microphone
- Records until silence detected (VAD threshold: 1.5s silence = end of answer)
- Sends audio as base64 blob over WebSocket

### Step 7 — STT transcribes answer
- `stt.py` calls Groq Whisper Large V3 Turbo
- Returns transcript → stored in `AgentState.conversation_history`

### Step 8 — Evaluation Agent scores
- Runs synchronously within LangGraph node
- `EvaluationResult` appended to `AgentState.evaluations`
- If `weak_areas` detected → Celery task dispatched for resource fetching

### Step 9 — Loop decision
- LangGraph conditional edge: `questions_asked < total_rounds` → go to `interview_agent`
- `questions_asked >= total_rounds` OR LLM outputs `INTERVIEW_COMPLETE` → go to `feedback_agent`

### Step 10 — Feedback generated
- Feedback Agent receives full session state
- Generates `FeedbackReport` JSON
- Stored at `session:{session_id}:report`

### Step 11 — Resources assembled
- Celery results collected (all resource fetch tasks should be done by now)
- Resources stored at `session:{session_id}:resources`

### Step 12 — Twilio delivery
- SMS sent: short summary + top 3 resource links
- WhatsApp sent (if opted in): full report link + revision Q&A

### Step 13 — Frontend shows report
- WebSocket sends `{ type: "interview_complete", session_id }`
- Frontend redirects to `/report/{session_id}`
- `GET /report/{session_id}` returns full `FeedbackReport` + resources

---

