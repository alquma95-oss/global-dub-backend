from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp
import requests
import uuid
import os

app = FastAPI()

# ========== Request Model ==========
class RequestModel(BaseModel):
    url: str
    target_language: str


# ========== Translate Endpoint ==========
@app.post("/translate")
async def translate_video(req: RequestModel):

    # ===== 1. Download Audio from YouTube =====
    audio_filename = f"audio_{uuid.uuid4()}.mp3"

    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "outtmpl": audio_filename,

        # ========== BOT DETECTION BYPASS ==========
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
                "player_skip": ["configs"],
            }
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 (KHTML, like Gecko)",
            "Accept-Language": "en-US,en;q=0.5"
        }
    }

    # Clean YouTube URL
    clean_url = req.url.split("&")[0].split("?si")[0]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(clean_url, download=True)
            except:
                # fallback mode
                info = ydl.extract_info(f"ytsearch:{clean_url}", download=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download audio: {str(e)}")


    # ===== 2. Convert speech to text (OpenAI Whisper) =====
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_KEY:
        raise HTTPException(status_code=500, detail="Missing OpenAI API Key")

    whisper_url = "https://api.openai.com/v1/audio/transcriptions"

    with open(audio_filename, "rb") as f:
        whisper_payload = {
            "model": "gpt-4o-transcribe",
        }
        whisper_files = {
            "file": (audio_filename, f, "audio/mpeg")
        }

        whisper_headers = {
            "Authorization": f"Bearer {OPENAI_KEY}"
        }

        try:
            whisper_res = requests.post(
                whisper_url,
                data=whisper_payload,
                headers=whisper_headers,
                files=whisper_files
            )
            text = whisper_res.json().get("text")
        except:
            raise HTTPException(status_code=500, detail="Transcription failed")


    # ===== 3. Translate Text =====
    translate_url = "https://api.openai.com/v1/chat/completions"
    translate_payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Translate text accurately with natural emotion."},
            {"role": "user", "content": f"Translate to {req.target_language}: {text}"}
        ]
    }

    try:
        trans_res = requests.post(
            translate_url,
            json=translate_payload,
            headers={"Authorization": f"Bearer {OPENAI_KEY}"}
        )
        translated_text = trans_res.json()["choices"][0]["message"]["content"]
    except:
        raise HTTPException(status_code=500, detail="Translation failed")


    # ===== 4. Generate Voice (ElevenLabs Natural Emotion Voice) =====
    ELEVEN_KEY = os.getenv("ELEVEN_API_KEY")
    if not ELEVEN_KEY:
        raise HTTPException(status_code=500, detail="Missing ElevenLabs API Key")

    voice_id = "21m00Tcm4TlvDq8ikWAM"   # Rachel (best natural emotion voice)

    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    tts_payload = {
        "text": translated_text,
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.9,
            "style": 0.6,
            "use_speaker_boost": True
        }
    }

    headers = {
        "xi-api-key": ELEVEN_KEY,
        "Content-Type": "application/json"
    }

    audio_output = f"output_{uuid.uuid4()}.mp3"

    try:
        res = requests.post(tts_url, json=tts_payload, headers=headers)
        with open(audio_output, "wb") as f:
            f.write(res.content)
    except:
        raise HTTPException(status_code=500, detail="Voice generation failed")


    # ===== 5. Return audio URL =====
    return {"audio_url": audio_output}
