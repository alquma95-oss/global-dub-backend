from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import uuid
import edge_tts

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RequestModel(BaseModel):
    video_url: str
    language: str

@app.post("/translate")
async def translate_video(req: RequestModel):
    url = req.video_url
    lang = req.language.lower()

    audio_file = f"audio_{uuid.uuid4()}.mp3"
    final_audio = f"output_{uuid.uuid4()}.mp3"

    # DOWNLOAD WITHOUT COOKIES
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": audio_file,
        "noplaylist": True,
        "extract_flat": False,
        "nocheckcertificate": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        return {"error": f"Failed to download: {str(e)}"}

    # LANG → VOICE MAP
    VOICES = {
        "english": "en-US-JennyNeural",
        "hindi": "hi-IN-SwaraNeural",
        "korean": "ko-KR-SunHiNeural",
        "japanese": "ja-JP-NanamiNeural",
        "arabic": "ar-EG-SalmaNeural"
    }

    if lang not in VOICES:
        return {"error": "Language not supported"}

    # TTS
    try:
        tts = edge_tts.Communicate("This is test translated audio", VOICES[lang])
        await tts.save(final_audio)
    except Exception as e:
        return {"error": f"TTS Error: {str(e)}"}

    return {"audio_url": f"https://global-dub-backend.onrender.com/{final_audio}"}
