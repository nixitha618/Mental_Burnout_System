"""
Database operations for user history and assessments
"""

from datetime import datetime, timedelta
from sqlalchemy import desc
from src.database.models import User, Assessment, get_session, init_database
import uuid

class DatabaseOps:
    def __init__(self):
        init_database()
        self.session = get_session()
    
    # User Operations
    def create_user(self, name=None, email=None):
        """Create a new user"""
        user_id = f"USER_{uuid.uuid4().hex[:8].upper()}"
        user = User(
            user_id=user_id,
            name=name,
            email=email
        )
        self.session.add(user)
        self.session.commit()
        print(f"✅ User created: {user_id}")
        return user
    
    def get_user(self, user_id):
        """Get user by ID"""
        return self.session.query(User).filter(User.user_id == user_id).first()
    
    def get_or_create_user(self, user_id=None, name=None, email=None):
        """Get existing user or create new one"""
        if user_id:
            user = self.get_user(user_id)
            if user:
                return user
        return self.create_user(name, email)
    
    # Assessment Operations
    def save_assessment(self, user_id, input_data, prediction):
        """Save an assessment to database"""
        user = self.get_user(user_id)
        if not user:
            user = self.create_user()
        
        assessment = Assessment(
            user_id=user.id,
            sleep_hours=input_data.get('sleep_hours'),
            workload_hours=input_data.get('workload_hours'),
            stress_level=input_data.get('stress_level'),
            screen_time=input_data.get('screen_time'),
            physical_activity=input_data.get('physical_activity'),
            social_interaction=input_data.get('social_interaction'),
            meal_quality=input_data.get('meal_quality'),
            productivity_score=input_data.get('productivity_score'),
            risk_level=prediction.get('risk_level'),
            risk_score=prediction.get('risk_score'),
            confidence=prediction.get('confidence')
        )
        
        self.session.add(assessment)
        self.session.commit()
        
        # Update user's last active time
        user.last_active = datetime.utcnow()
        self.session.commit()
        
        print(f"✅ Assessment saved for user: {user.user_id}")
        return assessment
    
    def get_user_history(self, user_id, limit=10):
        """Get user's assessment history"""
        user = self.get_user(user_id)
        if not user:
            return []
        
        assessments = self.session.query(Assessment).filter(
            Assessment.user_id == user.id
        ).order_by(desc(Assessment.assessment_date)).limit(limit).all()
        
        return [a.to_dict() for a in assessments]
    
    def get_risk_trend(self, user_id, days=30):
        """Get risk trend for last N days"""
        user = self.get_user(user_id)
        if not user:
            return []
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        assessments = self.session.query(Assessment).filter(
            Assessment.user_id == user.id,
            Assessment.assessment_date >= cutoff_date
        ).order_by(Assessment.assessment_date).all()
        
        return [
            {
                'date': a.assessment_date.isoformat(),
                'risk_score': a.risk_score,
                'risk_level': a.risk_level
            }
            for a in assessments
        ]
    
    def get_statistics(self, user_id):
        """Get user statistics"""
        user = self.get_user(user_id)
        if not user:
            return {}
        
        assessments = self.session.query(Assessment).filter(
            Assessment.user_id == user.id
        ).all()
        
        if not assessments:
            return {'total_assessments': 0}
        
        risk_levels = [a.risk_level for a in assessments]
        avg_risk_score = sum(a.risk_score for a in assessments) / len(assessments)
        
        return {
            'total_assessments': len(assessments),
            'average_risk_score': round(avg_risk_score, 2),
            'risk_level_counts': {
                'Low': risk_levels.count('Low'),
                'Medium': risk_levels.count('Medium'),
                'High': risk_levels.count('High')
            },
            'first_assessment': assessments[0].assessment_date.isoformat(),
            'last_assessment': assessments[-1].assessment_date.isoformat()
        }
    
    def close(self):
        """Close database session"""
        self.session.close()

# Singleton instance
_db_ops = None

def get_db():
    global _db_ops
    if _db_ops is None:
        _db_ops = DatabaseOps()
    return _db_ops