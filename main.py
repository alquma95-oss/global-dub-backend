from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
from deep_translator import GoogleTranslator
import requests
import os

app = FastAPI()

# CORS for MIT App Inventor
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ELEVEN_API_KEY = os.environ.get("ELEVEN_API_KEY")

class RequestModel(BaseModel):
    url: str
    target_language: str


@app.post("/translate")
def translate_video(req: RequestModel):
    try:
        # 1 — YT Audio extract
        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "outtmpl": "audio.%(ext)s"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            audio_url = info["url"]

        # 2 — Transcript extract
        if "entries" in info:
            info = info["entries"][0]

        if "description" in info and info["description"]:
            text = info["description"]
        else:
            text = info.get("title", "")

        # 3 — Translate
        translated_text = GoogleTranslator(source="auto", target=req.target_language).translate(text)

        if not translated_text:
            raise HTTPException(status_code=400, detail="Translation failed")

        # 4 — Generate emotional dubbing via ElevenLabs
        voice_id = "EXAVITQu4vr4xnSDxMaL"  # Rachel emotional voice

        TTS_API = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        payload = {
            "text": translated_text,
            "voice_settings": {"stability": 0.2, "similarity_boost": 0.9}
        }

        headers = {
            "xi-api-key": ELEVEN_API_KEY,
            "Content-Type": "application/json"
        }

        audio_response = requests.post(TTS_API, json=payload, headers=headers)

        if audio_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Voice dubbing failed")

        # Save audio file
        with open("output.mp3", "wb") as f:
            f.write(audio_response.content)

        return {
            "status": "success",
            "translated_text": translated_text,
            "dub_url": "output.mp3"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
