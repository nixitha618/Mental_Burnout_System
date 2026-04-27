"""
Scheduler for automated email reports
"""

import threading
import time
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.services.email_service import get_email_service
from src.database.operations import get_db
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class EmailScheduler:
    def __init__(self):
        self.email_service = get_email_service()
        self.db = get_db()
        self.running = False
        self.thread = None
        
    def start(self):
        """Start the scheduler thread"""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("✅ Email scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Email scheduler stopped")
    
    def _run(self):
        """Main scheduler loop"""
        while self.running:
            try:
                # Check for weekly reports (every Monday at 9 AM)
                self._check_weekly_reports()
                
                # Check for high risk alerts (realtime, but we'll check every hour)
                self._check_subscriptions()
                
                # Sleep for 1 hour before next check
                time.sleep(3600)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)
    
    def _check_weekly_reports(self):
        """Check if it's time to send weekly reports"""
        now = datetime.now()
        
        # Check if it's Monday and between 9 AM and 10 AM
        if now.weekday() == 0 and 9 <= now.hour < 10:
            self._send_weekly_reports_to_all()
    
    def _send_weekly_reports_to_all(self):
        """Send weekly reports to all subscribed users"""
        try:
            # Load subscriptions
            subscriptions = self._load_subscriptions()
            
            for sub_key, sub_data in subscriptions.items():
                if sub_data.get('receive_weekly', True):
                    user_id = sub_data['user_id']
                    logger.info(f"Sending weekly report to {user_id}")
                    self.email_service.send_weekly_report(user_id)
                    
        except Exception as e:
            logger.error(f"Failed to send weekly reports: {e}")
    
    def _check_subscriptions(self):
        """Check subscription status (for future features)"""
        pass
    
    def _load_subscriptions(self):
        """Load subscriptions from file"""
        try:
            with open('data/subscriptions.json', 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def send_high_risk_alert_if_needed(self, user_id: str, assessment_data: dict, prediction: dict):
        """Send high risk alert if risk is high and user subscribed"""
        try:
            risk_score = prediction.get('risk_score', 0)
            
            # Check if risk is high (>60%)
            if risk_score >= 60:
                # Load subscriptions
                subscriptions = self._load_subscriptions()
                sub_key = f"sub_{user_id}"
                
                if sub_key in subscriptions and subscriptions[sub_key].get('receive_alerts', True):
                    logger.info(f"Sending high risk alert to {user_id}")
                    self.email_service.send_high_risk_alert(user_id, assessment_data, prediction)
                    
        except Exception as e:
            logger.error(f"Failed to check/send alert: {e}")

# Global scheduler instance
_scheduler = None

def get_scheduler():
    global _scheduler
    if _scheduler is None:
        _scheduler = EmailScheduler()
    return _scheduler

def start_scheduler():
    """Start the email scheduler"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler
