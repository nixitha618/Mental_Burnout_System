"""
Email service for sending notifications and reports
"""

import smtplib
import sqlite3
import json
import os
import sys

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from jinja2 import Template

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.config.email_config import get_email_config, is_email_configured, get_test_mode
from src.database.operations import get_db
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


# ══════════════════════════════════════════════════════════════
#  HELPER: resolve email from subscriptions.json OR DB
# ══════════════════════════════════════════════════════════════

def _resolve_email(user_id: str, db) -> Optional[str]:
    """
    Try every possible source to find the user's email:
      1. data/subscriptions.json  (most reliable — written at Subscribe time)
      2. DB user.email
    Returns None if nothing found.
    """
    # 1. subscriptions.json
    try:
        with open('data/subscriptions.json', 'r') as f:
            subs = json.load(f)
        entry = subs.get(f"sub_{user_id}")
        if entry and entry.get('email'):
            return entry['email'].strip().lower()
    except Exception:
        pass

    # 2. DB
    try:
        user = db.get_user(user_id)
        if user and user.email:
            return user.email.strip().lower()
    except Exception:
        pass

    return None


# ══════════════════════════════════════════════════════════════
#  HELPER: normalise a raw history record into a flat dict
#  DB records may store metrics inside a nested 'input_data'
#  or 'prediction' JSON column — handle both shapes.
# ══════════════════════════════════════════════════════════════

def _flatten_record(record: Any) -> dict:
    """
    Accept either a dict (already flat or nested) or a SQLAlchemy
    model object and return a flat dict with all metric keys at top level.
    """
    # Convert ORM object → dict if needed
    if hasattr(record, '__dict__'):
        raw = {k: v for k, v in record.__dict__.items() if not k.startswith('_')}
    elif isinstance(record, dict):
        raw = dict(record)
    else:
        raw = {}

    # Unwrap nested input_data / prediction JSON strings
    for key in ('input_data', 'prediction'):
        val = raw.get(key)
        if isinstance(val, str):
            try:
                raw.update(json.loads(val))
            except Exception:
                pass
        elif isinstance(val, dict):
            raw.update(val)

    return raw


class EmailService:
    def __init__(self):
        self.config = get_email_config()
        self.test_mode = get_test_mode()
        self.db = get_db()

    # ══════════════════════════════════════════════════════
    #  EMAIL RATE LIMIT
    # ══════════════════════════════════════════════════════

    def _can_send_email_today(self, user_id: str, limit: int = None) -> bool:
        if limit is None:
            limit = self.config.get('daily_email_limit', 15)
        try:
            conn = sqlite3.connect('data/burnout.db')
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    sent_at TIMESTAMP
                )
            """)
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute(
                "SELECT COUNT(*) FROM email_logs WHERE user_id = ? AND DATE(sent_at) = ?",
                (user_id, today)
            )
            count = cursor.fetchone()[0]
            conn.close()
            return count < limit
        except Exception as e:
            logger.error(f"Email limit check failed: {e}")
            return True

    def _log_email_sent(self, user_id: str):
        try:
            conn = sqlite3.connect('data/burnout.db')
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    sent_at TIMESTAMP
                )
            """)
            cursor.execute(
                "INSERT INTO email_logs (user_id, sent_at) VALUES (?, ?)",
                (user_id, datetime.now())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log email: {e}")

    # ══════════════════════════════════════════════════════
    #  BASE SMTP SENDER
    # ══════════════════════════════════════════════════════

    def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send email via SMTP. Respects test_mode flag."""

        if self.test_mode:
            logger.info(f"[TEST MODE] Would send email to: {to_email}")
            logger.info(f"[TEST MODE] Subject: {subject}")
            logger.info(f"[TEST MODE] Preview: {html_content[:300]}...")
            # ── In test mode we STILL return True so callers don't think it failed ──
            return True

        if not is_email_configured():
            logger.error("❌ Email not configured. Set SENDER_EMAIL and SENDER_PASSWORD in .env")
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"{self.config['subject_prefix']}{subject}"
            msg['From']    = self.config['sender_email']
            msg['To']      = to_email

            msg.attach(MIMEText(html_content, 'html'))

            with smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port']) as server:
                if self.config.get('use_tls', True):
                    server.starttls()
                server.login(self.config['sender_email'], self.config['sender_password'])
                server.send_message(msg)

            logger.info(f"✅ Email sent to {to_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("❌ SMTP authentication failed. Check SENDER_EMAIL / SENDER_PASSWORD (use Gmail App Password).")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            return False

    # ══════════════════════════════════════════════════════
    #  INLINE HTML FALLBACK (used when template file missing)
    # ══════════════════════════════════════════════════════

    def _inline_alert_html(self, user_name: str, risk_score: float, risk_level: str,
                           assessment_data: dict, concerning_factors: list) -> str:
        emoji = "🚨" if risk_level == "High" else "⚠️" if risk_level == "Medium" else "✅"
        color = "#ff6b6b" if risk_level == "High" else "#ffc542" if risk_level == "Medium" else "#10b981"
        
        # Build sections dynamically by risk level
        custom_sections_html = ""
        if risk_level == "High":
            factors_html = "".join(f"<li><b>{f['factor']}</b>: {f['message']}</li>" for f in concerning_factors)
            custom_sections_html = f"""
            <h3>⚠️ Concerning Factors</h3>
            <ul>{factors_html or "<li>None detected!</li>"}</ul>
            <h3>📞 Immediate Actions You Can Take</h3>
            <ul>
                <li>Take a 15-minute break right now</li>
                <li>Practice deep breathing exercises (4-7-8 technique)</li>
                <li>Talk to a trusted friend or family member</li>
                <li>Consider speaking with a mental health professional</li>
            </ul>
            <div style="background:#fee2e2;border:1px solid #ef4444;padding:10px;border-radius:5px;font-size:12px;color:#991b1b;margin-top:15px;text-align:center;">
                <strong>⚠️ Crisis Support:</strong> If you are in crisis or having thoughts of harm, contact emergency helplines immediately.
            </div>
            """
        elif risk_level == "Medium":
            factors_html = "".join(f"<li><b>{f['factor']}</b>: {f['message']}</li>" for f in concerning_factors)
            custom_sections_html = f"""
            <h3>⚠️ Concerning Factors</h3>
            <ul>{factors_html or "<li>None detected! Keep up the healthy routine.</li>"}</ul>
            <h3>💡 Recommended Actions to Reduce Burnout Risk</h3>
            <ul>
                <li>Try scheduling regular micro-breaks during work</li>
                <li>Set aside dedicated screen-free time in the evening</li>
                <li>Ensure you get at least 20-30 minutes of physical activity daily</li>
                <li>Reach out for social support or chat with team members</li>
            </ul>
            """
        else:
            custom_sections_html = """
            <h3>🎉 Healthy Habits & Wellness Tips</h3>
            <ul>
                <li>Continue prioritizing 7-8 hours of sleep nightly</li>
                <li>Maintain regular active physical exercise routines</li>
                <li>Keep setting clear work-life boundaries</li>
                <li>Practice gratitude or mindfulness to keep stress low</li>
            </ul>
            """

        return f"""
        <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
        <div style="max-width:600px;margin:auto;background:white;border-radius:10px;padding:30px;">
          <h1 style="color:{color};">{emoji} {risk_level} Burnout Risk Report</h1>
          <p>Hi <b>{user_name}</b>,</p>
          <p>Here is your recent burnout risk assessment report:</p>
          <div style="background:#f9f9f9;padding:15px;border-radius:8px;margin:15px 0;border-left:4px solid {color};">
            <p style="font-size:24px;font-weight:bold;margin:0;color:{color};">{risk_score}%</p>
            <p style="margin:5px 0 0;color:#666;">Risk Level: <b>{risk_level}</b></p>
          </div>
          <h3>📊 Assessment Details</h3>
          <ul>
            <li><b>Sleep Duration:</b> {assessment_data.get('sleep_hours','—')} hours</li>
            <li><b>Workload Hours:</b> {assessment_data.get('workload_hours','—')} hours</li>
            <li><b>Stress Level:</b> {assessment_data.get('stress_level','—')}/10</li>
            <li><b>Screen Time:</b> {assessment_data.get('screen_time','—')} hours</li>
            <li><b>Physical Activity:</b> {assessment_data.get('physical_activity','—')} mins</li>
            <li><b>Social Interaction:</b> {assessment_data.get('social_interaction','—')} hours</li>
          </ul>
          {custom_sections_html}
          <p style="color:#888;font-size:12px;">— MindGuard AI</p>
        </div></body></html>
        """

    def _inline_report_html(self, data: dict) -> str:
        recs_html = "".join(f"<li>{r}</li>" for r in data.get('recommendations', []))
        color = {'low': '#00e5c3', 'medium': '#ffc542', 'high': '#ff6b6b'}.get(
            data.get('risk_level_lower', 'medium'), '#ffc542')
        return f"""
        <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
        <div style="max-width:600px;margin:auto;background:white;border-radius:10px;padding:30px;">
          <h1 style="color:#7c5cfc;">🧠 MindGuard AI — Weekly Report</h1>
          <p>Hi <b>{data['user_name']}</b> | Week: {data['week_range']}</p>
          <h2>Average Risk Score:
            <span style="color:{color}">{data['avg_risk_score']}%
            ({data['risk_level_lower'].capitalize()})</span>
          </h2>
          <p>Trend: <b>{data['trend_display']}</b>
             ({'+' if data['trend_change'] >= 0 else ''}{data['trend_change']}%)</p>
          <h3>Weekly Breakdown ({data['total_assessments']} assessments)</h3>
          <ul>
            <li>🟢 Low: {data['low_days']}</li>
            <li>🟡 Medium: {data['medium_days']}</li>
            <li>🔴 High: {data['high_days']}</li>
          </ul>
          <h3>Average Metrics</h3>
          <ul>
            <li>Sleep: {data['avg_sleep']} hrs</li>
            <li>Stress: {data['avg_stress']}/10</li>
            <li>Workload: {data['avg_workload']} hrs</li>
            <li>Activity: {data['avg_activity']} mins</li>
            <li>Social: {data['avg_social']} hrs</li>
          </ul>
          <h3>Recommendations</h3>
          <ul>{recs_html}</ul>
          <p style="color:#888;font-size:12px;">— MindGuard AI</p>
        </div></body></html>
        """

    # ══════════════════════════════════════════════════════
    #  HIGH-RISK ALERT
    # ══════════════════════════════════════════════════════

    def send_high_risk_alert(self, user_id: str,
                             assessment_data: Dict, prediction: Dict,
                             ignore_preferences: bool = False) -> bool:
        try:
            # ── 1. Resolve email ──
            email = _resolve_email(user_id, self.db)
            if not email:
                logger.error(f"❌ No valid email found for user {user_id}. "
                             "Ask user to subscribe on Notifications page.")
                return False

            # ── 2. Rate limit ──
            if not self._can_send_email_today(user_id):
                logger.warning("❌ Email limit reached for today")
                return False

            # ── 2b. Check alert preference & risk level ──
            receive_alerts = True
            try:
                with open('data/subscriptions.json', 'r') as f:
                    subs = json.load(f)
                entry = subs.get(f"sub_{user_id}", {})
                if entry:
                    receive_alerts = entry.get('receive_alerts', True)
            except Exception:
                pass

            risk_level = prediction.get('risk_level', 'Medium')
            risk_score = round(prediction.get('risk_score', 0), 1)

            # If user has NOT subscribed to instant report, we ONLY send it automatically if it is High risk alert
            if not ignore_preferences and not receive_alerts:
                if risk_level != 'High' or risk_score < 60:
                    logger.info(f"⏭️ Skipping assessment report for user {user_id} (not high risk and opted out of instant reports)")
                    return False
                else:
                    logger.info(f"🚨 Automatic High Risk Alert triggered for user {user_id}")
            else:
                logger.info(f"📧 Instant Assessment Report triggered for user {user_id}")

            # ── 3. Resolve user name ──
            user_name = user_id
            try:
                user = self.db.get_user(user_id)
                if user and user.name:
                    user_name = user.name
            except Exception:
                pass

            # ── Also try subscriptions.json for name ──
            try:
                with open('data/subscriptions.json', 'r') as f:
                    subs = json.load(f)
                entry = subs.get(f"sub_{user_id}", {})
                if entry.get('name'):
                    user_name = entry['name']
            except Exception:
                pass

            # ── 4. Build concerning factors ──
            concerning_factors = []
            if assessment_data.get('sleep_hours', 10) < 6:
                concerning_factors.append({'factor': 'Sleep',
                    'message': 'Insufficient sleep increases burnout risk'})
            if assessment_data.get('stress_level', 0) > 7:
                concerning_factors.append({'factor': 'Stress',
                    'message': 'High stress levels are a primary burnout indicator'})
            if assessment_data.get('workload_hours', 0) > 10:
                concerning_factors.append({'factor': 'Workload',
                    'message': 'Excessive workload hours increase burnout risk'})
            if assessment_data.get('physical_activity', 100) < 20:
                concerning_factors.append({'factor': 'Physical Activity',
                    'message': 'Low physical activity may contribute to burnout'})
            if assessment_data.get('social_interaction', 10) < 1:
                concerning_factors.append({'factor': 'Social Interaction',
                    'message': 'Limited social interaction can increase isolation'})

            # ── 5. Try HTML template, fall back to inline ──
            template_path = (
                Path(__file__).resolve().parent.parent.parent
                / "templates" / "emails" / "high_risk_alert.html"
            )
            if template_path.exists():
                with open(template_path, 'r', encoding='utf-8') as f:
                    template = Template(f.read())
                html_content = template.render(
                    user_name=user_name,
                    risk_level=risk_level,
                    risk_score=risk_score,
                    sleep_hours=assessment_data.get('sleep_hours', 0),
                    workload_hours=assessment_data.get('workload_hours', 0),
                    stress_level=assessment_data.get('stress_level', 0),
                    screen_time=assessment_data.get('screen_time', 0),
                    physical_activity=assessment_data.get('physical_activity', 0),
                    social_interaction=assessment_data.get('social_interaction', 0),
                    concerning_factors=concerning_factors,
                    dashboard_url='http://localhost:8001'
                )
            else:
                logger.warning("⚠️ high_risk_alert.html template missing — using inline HTML")
                html_content = self._inline_alert_html(
                    user_name, risk_score, risk_level, assessment_data, concerning_factors)

            # ── 6. Send ──
            emoji = "🚨" if risk_level == "High" else "⚠️" if risk_level == "Medium" else "✅"
            subject = f"{emoji} MindGuard AI — {risk_level} Burnout Risk Report"

            success = self.send_email(
                to_email=email,
                subject=subject,
                html_content=html_content
            )
            if success:
                self._log_email_sent(user_id)
            return success

        except Exception as e:
            logger.error(f"❌ Failed to send high risk alert: {e}")
            import traceback; traceback.print_exc()
            return False

    # ══════════════════════════════════════════════════════
    #  WEEKLY REPORT
    # ══════════════════════════════════════════════════════

    def send_weekly_report(self, user_id: str, ignore_preferences: bool = False) -> bool:
        try:
            # ── 1. Resolve email ──
            email = _resolve_email(user_id, self.db)
            if not email:
                logger.error(f"❌ No valid email found for user {user_id}. "
                             "Ask user to subscribe on Notifications page.")
                return False

            # ── Check weekly report preference ──
            if not ignore_preferences:
                try:
                    with open('data/subscriptions.json', 'r') as f:
                        subs = json.load(f)
                    entry = subs.get(f"sub_{user_id}", {})
                    if entry and not entry.get('receive_weekly', True):
                        logger.info(f"⏭️ Skipping weekly report for user {user_id} (opted out)")
                        return False
                except Exception:
                    pass

            logger.info(f"📧 Preparing weekly report for: {email}")

            # ── 2. Resolve user name ──
            user_name = user_id
            try:
                user = self.db.get_user(user_id)
                if user and user.name:
                    user_name = user.name
            except Exception:
                pass
            try:
                with open('data/subscriptions.json', 'r') as f:
                    subs = json.load(f)
                entry = subs.get(f"sub_{user_id}", {})
                if entry.get('name'):
                    user_name = entry['name']
            except Exception:
                pass

            # ── 3. Fetch and flatten history ──
            cutoff_date = datetime.now() - timedelta(days=7)
            raw_history  = self.db.get_user_history(user_id, limit=100)

            # Flatten every record so metric keys are at the top level
            history = [_flatten_record(r) for r in raw_history]

            logger.info(f"📊 Raw history count: {len(history)}")
            if history:
                logger.info(f"📊 Sample record keys: {list(history[0].keys())}")

            # Filter to last 7 days
            weekly = []
            for rec in history:
                date_str = rec.get('created_at') or rec.get('date') or ''
                if date_str:
                    try:
                        dt = datetime.fromisoformat(
                            date_str.replace('Z', '+00:00').replace('+00:00', ''))
                        if dt >= cutoff_date:
                            weekly.append(rec)
                    except Exception:
                        pass

            # Fallback: use last 5 records regardless of date
            if not weekly:
                logger.warning("⚠️ No records in last 7 days — using last 5 records")
                weekly = history[:5]

            if not weekly:
                logger.error("❌ No assessment data found at all for this user")
                return False

            logger.info(f"📊 Using {len(weekly)} records for report")

            # ── 4. Compute metrics safely ──
            def safe_avg(key, default=0):
                vals = []
                for rec in weekly:
                    v = rec.get(key)
                    if v is not None:
                        try:
                            vals.append(float(v))
                        except (TypeError, ValueError):
                            pass
                return round(sum(vals) / len(vals), 1) if vals else default

            avg_sleep    = safe_avg('sleep_hours',       7.0)
            avg_stress   = safe_avg('stress_level',      5.0)
            avg_workload = safe_avg('workload_hours',     8.0)
            avg_activity = safe_avg('physical_activity', 30.0)
            avg_social   = safe_avg('social_interaction', 2.0)

            risk_scores = []
            for rec in weekly:
                v = rec.get('risk_score')
                if v is not None:
                    try:
                        risk_scores.append(float(v))
                    except (TypeError, ValueError):
                        pass

            avg_risk = round(sum(risk_scores) / len(risk_scores), 1) if risk_scores else 50.0

            # ── 5. Risk level ──
            if avg_risk < 33:
                risk_level_lower = 'low'
            elif avg_risk < 66:
                risk_level_lower = 'medium'
            else:
                risk_level_lower = 'high'

            # ── 6. Counts ──
            total  = len(weekly)
            low_c  = sum(1 for r in weekly if str(r.get('risk_level', '')).lower() == 'low')
            med_c  = sum(1 for r in weekly if str(r.get('risk_level', '')).lower() == 'medium')
            high_c = sum(1 for r in weekly if str(r.get('risk_level', '')).lower() == 'high')

            # ── 7. Trend (newest - oldest) ──
            if len(risk_scores) >= 2:
                trend_change = round(risk_scores[0] - risk_scores[-1], 1)
            else:
                trend_change = 0.0

            if trend_change > 2:
                trend, trend_display = 'up', 'Increasing'
            elif trend_change < -2:
                trend, trend_display = 'down', 'Decreasing'
            else:
                trend, trend_display = 'stable', 'Stable'

            # ── 8. Recommendations based on average risk score ──
            recommendations = []
            if avg_risk < 33.0:
                recommendations.append("🎉 Your average burnout risk is Low. Excellent job maintaining a healthy balance!")
                if avg_sleep < 7:
                    recommendations.append("🛌 Consider slightly increasing sleep duration to sustain your energy.")
                if avg_activity < 20:
                    recommendations.append("🏃 Keep moving! Adding short walks will help maintain your low risk.")
            elif avg_risk < 66.0:
                recommendations.append("⚠️ Your average burnout risk is Medium. Consider pacing yourself and adjusting daily routines.")
                if avg_stress > 6:
                    recommendations.append("🧘 Practice regular stress management techniques (like deep breathing or meditation).")
                if avg_workload > 9:
                    recommendations.append("⚖️ Set clear boundaries between work and personal life to prevent burnout escalation.")
                if avg_sleep < 7:
                    recommendations.append("🛌 Prioritize getting 7–9 hours of restful sleep nightly.")
                if avg_activity < 20:
                    recommendations.append("🚶 Try incorporating 20-30 minutes of physical activity daily.")
            else:
                recommendations.append("🚨 Your average burnout risk is High. Urgent workload reduction and self-care are highly recommended.")
                recommendations.append("🛑 Actively reduce your daily workload hours and delegate tasks where possible.")
                recommendations.append("💤 Prioritize deep rest: aim for 8+ hours of sleep and take screen-free downtime.")
                if avg_stress > 6:
                    recommendations.append("🧘 Reach out to a wellness counselor or manager to address stress triggers.")
                if avg_social < 1:
                    recommendations.append("👥 Do not isolate yourself; seek support from close friends or family.")

            # ── 9. Build template data ──
            template_data = {
                'user_name':         user_name,
                'avg_risk_score':    avg_risk,
                'risk_level_lower':  risk_level_lower,
                'week_range': (
                    f"{cutoff_date.strftime('%b %d')} – "
                    f"{datetime.now().strftime('%b %d, %Y')}"
                ),
                'trend':             trend,
                'trend_display':     trend_display,
                'trend_change':      trend_change,
                'total_assessments': total,
                'low_days':          low_c,
                'medium_days':       med_c,
                'high_days':         high_c,
                'avg_sleep':         avg_sleep,
                'avg_stress':        avg_stress,
                'avg_workload':      avg_workload,
                'avg_activity':      avg_activity,
                'avg_social':        avg_social,
                'recommendations':   recommendations,
                'dashboard_url':     'http://localhost:8001',
            }

            logger.info(f"📊 Template data: {template_data}")

            # ── 10. Try Jinja template, fall back to inline HTML ──
            template_path = (
                Path(__file__).resolve().parent.parent.parent
                / "templates" / "emails" / "weekly_report.html"
            )
            if template_path.exists():
                with open(template_path, 'r', encoding='utf-8') as f:
                    html_content = Template(f.read()).render(**template_data)
            else:
                logger.warning("⚠️ weekly_report.html template missing — using inline HTML")
                html_content = self._inline_report_html(template_data)

            # ── 11. Send ──
            success = self.send_email(
                to_email=email,
                subject=f"🧠 MindGuard AI — Weekly Burnout Report "
                        f"({datetime.now().strftime('%b %d, %Y')})",
                html_content=html_content
            )
            if success:
                logger.info(f"✅ Weekly report sent to {email}")
                self._log_email_sent(user_id)
            else:
                logger.error("❌ send_email returned False")

            return success

        except Exception as e:
            logger.error(f"❌ Failed to send weekly report: {e}")
            import traceback; traceback.print_exc()
            return False


# ── Singleton ──
_email_service = None

def get_email_service():
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service