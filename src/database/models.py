"""
Database models for user history and tracking
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from pathlib import Path

Base = declarative_base()

class User(Base):
    """User model for authentication and tracking"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100))
    email = Column(String(100), unique=True)
    password = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    assessments = relationship("Assessment", back_populates="user", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.user_id,
            'name': self.name,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_active': self.last_active.isoformat() if self.last_active else None
        }

class Assessment(Base):
    """Store each burnout assessment"""
    __tablename__ = 'assessments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    assessment_date = Column(DateTime, default=datetime.utcnow)
    
    # Input features
    sleep_hours = Column(Float)
    workload_hours = Column(Float)
    stress_level = Column(Integer)
    screen_time = Column(Float)
    physical_activity = Column(Integer)
    social_interaction = Column(Float)
    meal_quality = Column(Integer)
    productivity_score = Column(Integer)
    
    # Prediction results
    risk_level = Column(String(10))
    risk_score = Column(Float)
    confidence = Column(Float)
    
    # Additional metadata
    notes = Column(String(500), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="assessments")
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.assessment_date.isoformat() if self.assessment_date else None,
            'sleep_hours': self.sleep_hours,
            'workload_hours': self.workload_hours,
            'stress_level': self.stress_level,
            'screen_time': self.screen_time,
            'physical_activity': self.physical_activity,
            'social_interaction': self.social_interaction,
            'meal_quality': self.meal_quality,
            'productivity_score': self.productivity_score,
            'risk_level': self.risk_level,
            'risk_score': self.risk_score,
            'confidence': self.confidence
        }

# Database setup
def get_database_path():
    db_dir = Path(__file__).resolve().parent.parent.parent / "data"
    db_dir.mkdir(exist_ok=True)
    return db_dir / "burnout.db"

def init_database():
    """Initialize database and create tables"""
    db_path = get_database_path()
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    Base.metadata.create_all(engine)
    print(f"✅ Database initialized at: {db_path}")
    return engine

def get_session():
    """Get database session"""
    engine = init_database()
    Session = sessionmaker(bind=engine)
    return Session()

if __name__ == "__main__":
    init_database()
    print("✅ Database models created successfully!")