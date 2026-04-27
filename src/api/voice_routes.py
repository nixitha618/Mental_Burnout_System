from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import os, json, logging, wave, io
import httpx
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE = "https://api.groq.com/openai/v1"

SYS_PROMPT = (
    "You are a helpful, friendly AI voice assistant. "
    "Keep replies SHORT and natural."
)


# ── HELPERS ─────────────────────────────────────────

async def send(ws, data):
    try:
        await ws.send_text(json.dumps(data))
    except:
        pass


async def transcribe(pcm_bytes: bytes):
    buf = io.BytesIO()

    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(pcm_bytes)

    buf.seek(0)

    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{GROQ_BASE}/audio/transcriptions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            files={"file": ("speech.wav", buf, "audio/wav")},
            data={"model": "whisper-large-v3-turbo"},
        )
        r.raise_for_status()
        return r.json().get("text", "").strip()


async def llm_reply(history):
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(
            f"{GROQ_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": history
            },
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


async def tts(text):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{GROQ_BASE}/audio/speech",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "canopylabs/orpheus-v1-english",
                "input": text[:200],
                "voice": "autumn",
                "response_format": "wav",
            },
        )
        return r.content


# ── WEBSOCKET ───────────────────────────────────────

@router.websocket("/voice/ws")   # ✅ IMPORTANT
async def voice_ws(ws: WebSocket):
    await ws.accept()

    history = [{"role": "system", "content": SYS_PROMPT}]
    audio_buf = bytearray()

    await send(ws, {"type": "status", "state": "ready"})

    try:
        while True:
            try:
               msg = await ws.receive()
            except RuntimeError:
        # 🔥 Client disconnected safely
                   break


            if "bytes" in msg:
                audio_buf.extend(msg["bytes"])

            elif "text" in msg:
                data = json.loads(msg["text"])

                if data.get("type") == "end_of_speech":

                    if len(audio_buf) < 8000:
                        audio_buf.clear()
                        await send(ws, {"type": "error", "text": "Speak louder"})
                        continue

                    pcm = bytes(audio_buf)
                    audio_buf.clear()

                    # STT
                    transcript = await transcribe(pcm)

                    await send(ws, {"type": "transcript", "text": transcript})

                    # LLM
                    history.append({"role": "user", "content": transcript})
                    reply = await llm_reply(history)
                    history.append({"role": "assistant", "content": reply})

                    await send(ws, {"type": "response", "text": reply})

                    # TTS
                    audio = await tts(reply)
                    await ws.send_bytes(audio)

    except WebSocketDisconnect:
        logger.info("Disconnected")