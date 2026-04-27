
"""
Email configuration for notifications and reports
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Email Configuration
EMAIL_CONFIG = {
    # For Gmail users (use App Password, not regular password)
    "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("SMTP_PORT", 587)),
    "sender_email": os.getenv("SENDER_EMAIL", ""),
    "sender_password": os.getenv("SENDER_PASSWORD", ""),
    
    # For testing (print emails instead of sending)
    "test_mode": os.getenv("EMAIL_TEST_MODE", "True").lower() == "true",
    
    # Email settings
    "use_tls": True,
    "subject_prefix": "[MindGuard AI] ",
}

# Report Settings
REPORT_SETTINGS = {
    "weekly_report_day": "Monday",  # Day to send weekly reports
    "weekly_report_time": "09:00",   # Time to send reports
    "high_risk_threshold": 60,       # Risk score above this triggers alert
    "medium_risk_threshold": 30,     # Risk score above this is medium
}

# Email Templates Directory
TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates" / "emails"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

def get_email_config():
    """Get email configuration"""
    return EMAIL_CONFIG

def is_email_configured():
    """Check if email is properly configured"""
    config = get_email_config()
    return bool(config["sender_email"] and config["sender_password"])

def get_test_mode():
    """Get test mode status"""
    return get_email_config()["test_mode"]
