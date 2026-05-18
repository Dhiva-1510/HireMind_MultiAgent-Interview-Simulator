import os
from groq import Groq
from twilio.twiml.messaging_response import MessagingResponse

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are HireMind, an expert interview coach and technical mentor.
When a candidate asks you any concept or topic, explain it briefly and clearly for interview preparation.

Rules:
- Keep answers concise (max 200 words) — perfect for quick revision before an interview
- Use bullet points for clarity where needed
- Always relate your answer to how it would be used in a real interview context
- If asked a coding concept, give a 1-2 line code snippet example if helpful
- End every reply with 1 tip: "Interview Tip: ..." related to the topic
- Never refuse to answer a technical question
"""

def handle_incoming_sms(incoming_message: str) -> str:
    """
    Processes an incoming SMS/WhatsApp message and returns
    a brief, interview-focused AI response using Groq.
    """
    if not incoming_message or not incoming_message.strip():
        return "Hi! I am HireMind, your interview prep assistant. Ask me any technical concept (e.g. 'Explain OOPs') and I will give you a quick revision answer!"

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": incoming_message.strip()}
            ],
            temperature=0.5,
            max_tokens=400
        )
        return completion.choices[0].message.content

    except Exception as e:
        return f"Sorry, I could not process your question right now. Error: {str(e)}"


def build_twiml_response(answer: str) -> str:
    """Wraps the answer in a Twilio TwiML MessagingResponse."""
    resp = MessagingResponse()
    resp.message(answer)
    return str(resp)
