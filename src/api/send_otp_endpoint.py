import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# ── Load env ─────────────────────────────────────────────
load_dotenv()

SMTP_SERVER   = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", 587))
SENDER_EMAIL  = os.getenv("SENDER_EMAIL", "")
SENDER_PASS   = os.getenv("SENDER_PASSWORD", "")

logger = logging.getLogger("mindguard.otp")

# ── Router ─────────────────────────────────────────────
router = APIRouter()

# ── Request Model ──────────────────────────────────────
class OTPRequest(BaseModel):
    email: str
    otp: str
    mode: str = "login"
    name: str = "there"

# ── API Endpoint ───────────────────────────────────────
@router.post("/send_otp")
async def send_otp(data: OTPRequest):

    if not data.email or not data.otp:
        raise HTTPException(status_code=400, detail="email and otp are required")

    try:
        _send_email(data.email, data.otp, data.mode, data.name)
        logger.info(f"OTP sent to {data.email}")
        return {"ok": True}

    except Exception as e:
        logger.exception("Failed to send OTP")
        raise HTTPException(status_code=500, detail=str(e))


# ── EMAIL FUNCTION ─────────────────────────────────────
def _send_email(to_email: str, otp: str, mode: str, name: str):

    if mode == "reset":
        subject = "[MindGuard AI] Reset your password"
    else:
        subject = "[MindGuard AI] Your verification code"

    html = f"""
    <h2>MindGuard AI</h2>
    <p>Hello {name},</p>
    <p>Your OTP is:</p>
    <h1>{otp}</h1>
    <p>This code expires in 5 minutes.</p>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASS)
        server.send_message(msg)