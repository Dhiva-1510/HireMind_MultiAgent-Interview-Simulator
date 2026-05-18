import os
import tempfile
import requests
from groq import Groq
import asyncio
import edge_tts

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def transcribe_audio(audio_path):
    if not audio_path:
        return ""
    try:
        with open(audio_path, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
              file=(os.path.basename(audio_path), file.read()),
              model="whisper-large-v3-turbo",
              prompt="Interview answer.",
              response_format="text",
              language="en"
            )
        return transcription
    except Exception as e:
        return f"[Error transcribing audio: {str(e)}]"

def generate_tts(text):
    """
    Generates TTS. Attempts to use canopylabs/orpheus-v1-english if API is provided,
    otherwise falls back to a free high-quality edge-tts.
    """
    if not text:
        return None
        
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_path = temp_file.name
    temp_file.close()

    # If the user wants to use Canopy Labs Orpheus
    canopy_key = os.getenv("CANOPY_API_KEY")
    if canopy_key:
        try:
            # Hypothetical implementation for Canopy Labs Orpheus TTS
            headers = {"Authorization": f"Bearer {canopy_key}", "Content-Type": "application/json"}
            payload = {"model": "canopylabs/orpheus-v1-english", "text": text}
            # url = "https://api.canopylabs.com/v1/audio/speech" # Placeholder URL
            # response = requests.post(url, json=payload, headers=headers)
            # if response.status_code == 200:
            #     with open(temp_path, "wb") as f:
            #         f.write(response.content)
            #     return temp_path
        except Exception as e:
            pass

    # Fallback to Edge TTS (Free, high quality)
    async def _generate():
        communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
        await communicate.save(temp_path)

    asyncio.run(_generate())
    return temp_path
