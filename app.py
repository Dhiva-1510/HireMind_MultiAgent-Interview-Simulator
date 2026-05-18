import gradio as gr
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

from resume_parser import parse_resume, get_profile
from agents import HireMindAgents
from voice import transcribe_audio, generate_tts
from resources import fetch_resources_for_weakness
from notifications import send_twilio_sms

from notifications import send_twilio_sms

session_agents = {}

def process_resume(file_path, phone_number, apt_q, tech_q, comm_q, resume_q):
    if not file_path:
        return "Please upload a resume.", None, gr.update(interactive=False), gr.update(interactive=False), gr.update(interactive=False), None, ""
    
    session_id = str(uuid.uuid4())
    
    try:
        profile = parse_resume(file_path, session_id)
        agent = HireMindAgents(session_id, apt_q, tech_q, comm_q, resume_q)
        agent.phone_number = phone_number
        session_agents[session_id] = agent
        
        first_q = agent.get_interview_question(profile, [], current_round=1)
        audio_file = generate_tts(first_q)
        
        return (
            f"Resume parsed! Profile created for {profile.get('name', 'Candidate')}.", 
            session_id,
            gr.update(interactive=True, value=""),  
            gr.update(interactive=True, value=None),
            gr.update(interactive=True),
            audio_file,
            first_q,
            1
        )
    except Exception as e:
        return f"Error parsing resume: {str(e)}", None, gr.update(), gr.update(), gr.update(), None, None, 1

def get_audio_html(file_path):
    if not file_path or not os.path.exists(file_path): return ""
    import base64
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f'<audio src="data:audio/mp3;base64,{b64}" autoplay style="display:none;"></audio>'

def chat_logic(user_message, user_audio, history, session_id, current_round):
    if not session_id or session_id not in session_agents:
        history.append({"role": "user", "content": user_message or "Audio input"})
        history.append({"role": "assistant", "content": "Error: Session expired or invalid. Please re-upload your resume."})
        yield "", None, history, current_round, None
        return
        
    agent = session_agents[session_id]
    profile = get_profile(session_id)
    
    # Process audio if provided
    if user_audio:
        transcription = transcribe_audio(user_audio)
        user_message = transcription if transcription else "[Unintelligible]"
    
    if not user_message:
        yield "", None, history, current_round, None
        return

    if not history:
        last_question = "Tell me about yourself." 
    else:
        last_question = history[-1].get("content", "Tell me about yourself.") if isinstance(history[-1], dict) else history[-1][1]
        
    # Evaluate
    eval_result = agent.evaluate_answer(last_question, user_message, profile)
    weak_areas = ", ".join(eval_result.get("weak_areas", [])) if eval_result.get("weak_areas") else "None"
    
    current_round += 1
    
    # Convert dict history to tuples for agent
    agent_history = []
    u_msg = ""
    for msg in history:
        if isinstance(msg, dict):
            if msg["role"] == "user": u_msg = msg["content"]
            elif msg["role"] == "assistant" and u_msg:
                agent_history.append([u_msg, msg["content"]])
                u_msg = ""
        else:
            agent_history.append(msg)
    
    agent_history.append([user_message, ""])
    
    next_question = agent.get_interview_question(profile, agent_history[:-1], current_round, weak_areas)
    
    if "INTERVIEW_COMPLETE" in next_question or current_round > agent.total_rounds:
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": "Interview complete! Generating your feedback report & finding learning resources... Please wait."})
        yield "", None, history, current_round, None
        
        # Generate feedback
        feedback = agent.generate_feedback(profile)
        
        # Get learning resources
        all_weak_areas = set()
        for e in agent.evaluations:
            all_weak_areas.update(e.get("weak_areas", []))
            
        resources = fetch_resources_for_weakness(", ".join(list(all_weak_areas)))
        
        if resources:
            feedback += "\n\n### Recommended Learning Resources:\n"
            for r in resources:
                feedback += f"- [{r['title']}]({r['url']}) (Topic: {r['topic']})\n"
                
        # Send Twilio SMS if phone number provided
        if getattr(agent, "phone_number", None):
            sms_body = f"HireMind Interview Complete!\nScore: {len(resources)} weak areas found.\nReview your feedback and learning resources."
            success, msg = send_twilio_sms(agent.phone_number, sms_body)
            if success:
                feedback += f"\n\n*(An SMS with a summary has been sent to {agent.phone_number})*"
            else:
                feedback += f"\n\n*(Failed to send SMS: {msg})*"
        
        history[-1]["content"] = "Interview complete! Here is your feedback:\n\n" + feedback
        final_audio = generate_tts("Interview complete. Please review your feedback report.")
        yield "", None, history, current_round, get_audio_html(final_audio)
    else:
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": next_question})
        next_audio = generate_tts(next_question)
        yield "", None, history, current_round, get_audio_html(next_audio)

with gr.Blocks(theme=gr.themes.Default(primary_hue="green", neutral_hue="slate")) as app:
    gr.Markdown("# HireMind AI Interview Simulator")
    gr.Markdown("Upload your resume. The AI will interview you with Voice and Text using the Canopy Labs Orpheus TTS fallback.")
    
    session_state = gr.State(None)
    round_state = gr.State(1)
    first_q_state = gr.State("")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 1. Candidate Setup")
            resume_input = gr.File(label="Upload Resume (PDF/DOCX)", file_types=[".pdf", ".docx"])
            phone_input = gr.Textbox(label="Phone Number for SMS (Optional)", placeholder="+1234567890")
            
            with gr.Row():
                apt_q = gr.Number(label="Aptitude Qs", value=1, precision=0, minimum=0)
                tech_q = gr.Number(label="Technical Qs", value=1, precision=0, minimum=0)
                comm_q = gr.Number(label="Communication Qs", value=1, precision=0, minimum=0)
                resume_q = gr.Number(label="Resume Qs", value=2, precision=0, minimum=0)
                
            parse_btn = gr.Button("Parse Resume & Start", variant="primary")
            status_output = gr.Textbox(label="Status", interactive=False)
            
        with gr.Column(scale=2):
            gr.Markdown("### 2. Live Interview")
            chatbot = gr.Chatbot(label="Interview Chat", height=400)
            
            with gr.Row():
                msg_input = gr.Textbox(label="Type your answer", placeholder="...", interactive=False, scale=2)
                audio_input = gr.Audio(sources=["microphone"], type="filepath", label="Or speak", interactive=False, scale=1)
            
            send_btn = gr.Button("Submit Answer", interactive=False)
            audio_output = gr.HTML()
            
    def init_chat(status, session_id, msg_val, audio_val, send_btn_status, audio_file, first_question, current_round):
        if first_question:
            return status, session_id, [{"role": "assistant", "content": first_question}], gr.update(interactive=True, value=""), gr.update(interactive=True, value=None), gr.update(interactive=True), get_audio_html(audio_file), current_round
        return status, session_id, [], gr.update(interactive=False), gr.update(interactive=False), gr.update(interactive=False), "", current_round
        
    parse_btn.click(
        fn=process_resume, 
        inputs=[resume_input, phone_input, apt_q, tech_q, comm_q, resume_q], 
        outputs=[status_output, session_state, msg_input, audio_input, send_btn, audio_output, first_q_state, round_state]
    ).then(
        fn=init_chat,
        inputs=[status_output, session_state, msg_input, audio_input, send_btn, audio_output, first_q_state, round_state],
        outputs=[status_output, session_state, chatbot, msg_input, audio_input, send_btn, audio_output, round_state]
    )
    
    send_btn.click(
        fn=chat_logic,
        inputs=[msg_input, audio_input, chatbot, session_state, round_state],
        outputs=[msg_input, audio_input, chatbot, round_state, audio_output]
    )

if __name__ == "__main__":
    app.launch()
