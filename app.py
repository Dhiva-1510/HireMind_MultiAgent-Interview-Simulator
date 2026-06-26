import os
import uuid
import shutil
import base64
import uvicorn
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Core Interview Logic & DB
from resume_parser import parse_resume, get_profile
from agents import HireMindAgents
from voice import transcribe_audio, generate_tts
from resources import fetch_resources_for_weakness
from database import create_user, authenticate_user, save_interview_session, get_user_sessions

import subprocess
print("[Auto-Build] Rebuilding frontend assets...")
try:
    res = subprocess.run("npm run build", shell=True, cwd="frontend", capture_output=True, text=True)
    print("[Auto-Build] STDOUT:\n", res.stdout)
    if res.returncode != 0:
        print("[Auto-Build] STDERR:\n", res.stderr)
    print(f"[Auto-Build] Complete. Exit code: {res.returncode}")
except Exception as e:
    print("[Auto-Build] Error compiling frontend:", e)

app = FastAPI(title="HireMind AI API Server")

# Allow CORS for local frontend development (Vite dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_agents = {}
agent_status = {}  # Tracks live processing stage per session_id

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str

@app.post("/api/auth/signup")
async def api_signup(req: SignupRequest):
    success, msg = create_user(req.name, req.email, req.password)
    if success:
        return {"message": msg}
    else:
        raise HTTPException(status_code=400, detail=msg)

@app.post("/api/auth/login")
async def api_login(req: LoginRequest):
    user = authenticate_user(req.email, req.password)
    if user:
        return {"user": {"name": user["name"], "email": user["email"]}}
    else:
        raise HTTPException(status_code=400, detail="Invalid email or password.")

@app.get("/api/interview/status/{session_id}")
async def api_interview_status(session_id: str):
    return {"status": agent_status.get(session_id, "idle")}

@app.get("/api/dashboard")
async def api_dashboard(email: str):
    sessions = get_user_sessions(email)
    return sessions

@app.post("/api/interview/start")
async def api_interview_start(
    resume: UploadFile = File(None),
    apt_q: int = Form(1),
    tech_q: int = Form(1),
    comm_q: int = Form(1),
    resume_q: int = Form(2),
    email: str = Form("anonymous"),
    target_role: str = Form(""),
    candidate_domain: str = Form(""),
    aptitude_types: str = Form("")
):
    os.makedirs("temp", exist_ok=True)
    file_path = None
    if resume:
        file_path = f"temp/{uuid.uuid4()}_{resume.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(resume.file, buffer)
    else:
        if os.path.exists("dummy_resume.docx"):
            file_path = "dummy_resume.docx"
        else:
            raise HTTPException(status_code=400, detail="Please upload a resume.")
            
    session_id = str(uuid.uuid4())
    try:
        profile = parse_resume(file_path, session_id)
        if target_role:
            profile["target_role"] = target_role
        if candidate_domain:
            profile["candidate_domain"] = candidate_domain

        agent = HireMindAgents(
            session_id, 
            apt_q, 
            tech_q, 
            comm_q, 
            resume_q,
            target_role=target_role,
            candidate_domain=candidate_domain,
            aptitude_types=aptitude_types
        )
        agent.email = email
        session_agents[session_id] = agent
        
        first_q_data = agent.get_interview_question(profile, [], current_round=1)
        first_q = first_q_data.get("question", "") if isinstance(first_q_data, dict) else first_q_data
        explanation = first_q_data.get("explanation", "") if isinstance(first_q_data, dict) else ""
        ideal = first_q_data.get("ideal_answer", "") if isinstance(first_q_data, dict) else ""
        company = first_q_data.get("company", "MNC") if isinstance(first_q_data, dict) else "MNC"
        
        # Save question to agent's history in standard flat format
        agent.history = [{"role": "assistant", "content": first_q}]
        
        audio_file = await generate_tts(first_q)
        audio_b64 = ""
        if audio_file and os.path.exists(audio_file):
            with open(audio_file, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode("utf-8")
                
        if file_path and file_path.startswith("temp/"):
            try: os.remove(file_path)
            except: pass
            
        return {
            "session_id": session_id,
            "first_q": first_q,
            "audio_b64": audio_b64,
            "explanation": explanation,
            "ideal_answer": ideal,
            "company": company
        }
    except Exception as e:
        if file_path and file_path.startswith("temp/"):
            try: os.remove(file_path)
            except: pass
        raise HTTPException(status_code=500, detail=f"Error starting interview: {str(e)}")

@app.post("/api/interview/chat")
async def api_interview_chat(
    session_id: str = Form(...),
    user_message: str = Form(""),
    user_audio: UploadFile = File(None),
    current_round: int = Form(...)
):
    if session_id not in session_agents:
        raise HTTPException(status_code=400, detail="Session expired or invalid.")
        
    agent = session_agents[session_id]
    profile = get_profile(session_id)
    
    # Step 1: Transcribe audio if provided
    if user_audio:
        agent_status[session_id] = "Transcribing your voice response..."
        os.makedirs("temp", exist_ok=True)
        audio_path = f"temp/{uuid.uuid4()}_audio.webm"
        with open(audio_path, "wb") as buffer:
            shutil.copyfileobj(user_audio.file, buffer)
            
        transcription = transcribe_audio(audio_path)
        user_message = transcription if transcription else "[Unintelligible]"
        
        try: os.remove(audio_path)
        except: pass
        
    if not user_message:
        raise HTTPException(status_code=400, detail="No answer message provided.")

    # Step 2: Extract last question from history
    last_question = "Tell me about yourself."
    if agent.history:
        for msg in reversed(agent.history):
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                last_question = msg["content"]
                break
    if "<details" in last_question:
        last_question = last_question.split("<details")[0].strip()

    # Step 3: Evaluate the answer
    agent_status[session_id] = "Evaluation Agent — Scoring your answer..."
    eval_result = agent.evaluate_answer(last_question, user_message, profile)
    weak_areas = ", ".join(eval_result.get("weak_areas", [])) if eval_result.get("weak_areas") else "None"
    
    current_round += 1
    
    # Append user answer to active history
    agent.history.append({"role": "user", "content": user_message})

    # Step 4: Generate next question or feedback
    agent_status[session_id] = "Question Agent — Generating next question..."
    next_q_data = agent.get_interview_question(profile, agent.history, current_round, weak_areas)
    next_question = next_q_data.get("question", "") if isinstance(next_q_data, dict) else next_q_data
    explanation = next_q_data.get("explanation", "") if isinstance(next_q_data, dict) else ""
    ideal = next_q_data.get("ideal_answer", "") if isinstance(next_q_data, dict) else ""
    company = next_q_data.get("company", "MNC") if isinstance(next_q_data, dict) else "MNC"
    
    audio_b64 = ""
    feedback = ""
    
    if "INTERVIEW_COMPLETE" in next_question or current_round > agent.total_rounds:
        agent_status[session_id] = "Feedback Agent — Writing your personalized report..."
        feedback = agent.generate_feedback(profile)
        
        all_weak_areas = set()
        for e in agent.evaluations:
            all_weak_areas.update(e.get("weak_areas", []))
            
        resources = fetch_resources_for_weakness(", ".join(list(all_weak_areas)))
        if resources:
            feedback += "\n\n### Recommended Learning Resources:\n"
            for r in resources:
                feedback += f"- [{r['title']}]({r['url']}) (Topic: {r['topic']})\n"
                
        if getattr(agent, "email", None):
            save_interview_session(agent.email, session_id, profile, agent.evaluations, feedback)
            if agent.email != "anonymous":
                import json
                import subprocess
                email_data = {
                    "email": agent.email,
                    "name": profile.get("name", "Candidate"),
                    "target_role": profile.get("target_role", "General Tech Role"),
                    "avg_score": f"{sum(e.get('overall_score', 0) for e in agent.evaluations) / max(1, len(agent.evaluations)):.1f}",
                    "feedback": feedback,
                    "evaluations": agent.evaluations
                }
                os.makedirs("temp", exist_ok=True)
                temp_json_path = f"temp/email_{session_id}.json"
                try:
                    with open(temp_json_path, "w", encoding="utf-8") as f:
                        json.dump(email_data, f)
                    subprocess.run(["node", "send_report.js", temp_json_path], env=os.environ, check=True)
                    url_file = temp_json_path + ".url"
                    if os.path.exists(url_file):
                        with open(url_file, "r") as f:
                            preview_url = f.read().strip()
                        feedback += f"\n\n*(Ethereal Test Email sent! Preview at: {preview_url})*"
                        try: os.remove(url_file)
                        except: pass
                    else:
                        feedback += f"\n\n*(Performance report emailed to {agent.email})*"
                except Exception as e:
                    print(f"Error sending email report: {e}")
                    feedback += f"\n\n*(Failed to send email report: {str(e)})*"
            
        agent_status[session_id] = "Voice Agent — Synthesizing audio..."
        audio_file = await generate_tts("Interview complete. Please review your feedback report.")
        if audio_file and os.path.exists(audio_file):
            with open(audio_file, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode("utf-8")
        agent_status[session_id] = "idle"
    else:
        agent.history.append({"role": "assistant", "content": next_question})
        agent_status[session_id] = "Voice Agent — Synthesizing audio..."
        audio_file = await generate_tts(next_question)
        if audio_file and os.path.exists(audio_file):
            with open(audio_file, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode("utf-8")
        agent_status[session_id] = "idle"
                
    return {
        "next_question": next_question,
        "audio_b64": audio_b64,
        "current_round": current_round,
        "explanation": explanation,
        "ideal_answer": ideal,
        "feedback": feedback,
        "company": company
    }

# Serve React static production build files
if os.path.exists("frontend/dist"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

    @app.get("/{catchall:path}")
    async def serve_react_app(catchall: str):
        # Prevent static files requests from falling into catch-all if they don't exist
        if catchall.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        return FileResponse("frontend/dist/index.html")

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=7860, reload=True)
