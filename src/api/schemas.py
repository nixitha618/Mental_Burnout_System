from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List
from datetime import datetime

class BurnoutInput(BaseModel):
    """Input schema for burnout prediction"""
    sleep_hours: float = Field(..., ge=0, le=24, description="Hours of sleep per night")
    workload_hours: float = Field(..., ge=0, le=24, description="Hours of work/study per day")
    stress_level: int = Field(..., ge=1, le=10, description="Stress level (1-10)")
    screen_time: float = Field(..., ge=0, le=24, description="Hours on digital devices")
    physical_activity: int = Field(..., ge=0, le=300, description="Minutes of exercise")
    social_interaction: float = Field(..., ge=0, le=24, description="Hours socializing")
    meal_quality: int = Field(..., ge=1, le=10, description="Meal quality (1-10)")
    productivity_score: int = Field(..., ge=1, le=10, description="Productivity score (1-10)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "sleep_hours": 7.5,
                "workload_hours": 8,
                "stress_level": 5,
                "screen_time": 6,
                "physical_activity": 30,
                "social_interaction": 2,
                "meal_quality": 7,
                "productivity_score": 7
            }
        }

class BurnoutPrediction(BaseModel):
    """Output schema for burnout prediction"""
    risk_level: str
    risk_score: float
    confidence: float
    all_probabilities: Dict[str, float]
    
class BurnoutExplanation(BaseModel):
    """Output schema for burnout explanation"""
    risk_level: str
    risk_score: float
    explanation: str
    concerning_factors: List[Dict]
    recommendations: List[str]
    global_feature_importance: Dict[str, float]

class GuidanceQuery(BaseModel):
    """Input schema for guidance query"""
    query: str
    context: Optional[Dict] = None

class GuidanceResponse(BaseModel):
    """Output schema for guidance response"""
    query: str
    response: str
    sources: Optional[List[str]] = None

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model_loaded: bool
    version: str = "1.0.0"