from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


from src.database.models import User


class UserSignup(BaseModel):
    email: str
    password: str
    name: str


class UserLogin(BaseModel):
    email: str
    password: str
import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.api.schemas import (
    BurnoutInput, BurnoutPrediction, BurnoutExplanation,
    GuidanceQuery, GuidanceResponse, HealthResponse
)
from src.ml.predictor import BurnoutPredictor
from src.ml.explainer import BurnoutExplainer
from src.rag.generator import get_generator
from src.rag.knowledge_base import get_knowledge_base
from src.utils.logger import setup_logger
from src.database.operations import get_db

router = APIRouter()
logger = setup_logger(__name__)

_predictor = None
_explainer = None

def get_predictor():
    global _predictor
    if _predictor is None:
        try:
            logger.info("🔄 Loading predictor model...")
            _predictor = BurnoutPredictor()
            logger.info("✅ Predictor loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load predictor: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")
    return _predictor

def get_explainer():
    global _explainer
    if _explainer is None:
        try:
            logger.info("🔄 Loading explainer model...")
            _explainer = BurnoutExplainer()
            logger.info("✅ Explainer loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load explainer: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load explainer: {str(e)}")
    return _explainer

# ==================== HEALTH ENDPOINTS ====================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    try:
        predictor = get_predictor()
        return HealthResponse(
            status="healthy",
            model_loaded=predictor.model is not None,
            version="1.0.0"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(status="degraded", model_loaded=False, version="1.0.0")

@router.get("/test")
async def test_endpoint():
    return {"message": "API is working!", "status": "ok"}

# ==================== PREDICTION ENDPOINTS ====================

@router.post("/predict", response_model=BurnoutPrediction)
async def predict_burnout(
    input_data: BurnoutInput,
    predictor: BurnoutPredictor = Depends(get_predictor)
):
    try:
        input_dict = input_data.dict()
        logger.info(f"📥 Received prediction request")
        prediction = predictor.predict(input_dict)
        logger.info(f"📤 Prediction result: {prediction['risk_level']}")
        return BurnoutPrediction(
            risk_level=prediction['risk_level'],
            risk_score=prediction['risk_score'],
            confidence=prediction['confidence'],
            all_probabilities=prediction['all_probabilities']
        )
    except Exception as e:
        logger.error(f"❌ Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@router.post("/explain", response_model=BurnoutExplanation)
async def explain_prediction(
    input_data: BurnoutInput,
    explainer: BurnoutExplainer = Depends(get_explainer)
):
    try:
        input_dict = input_data.dict()
        logger.info(f"📥 Received explanation request")
        explanation = explainer.explain_prediction(input_dict)
        logger.info(f"📤 Explanation result: {explanation['risk_level']}")
        return BurnoutExplanation(
            risk_level=explanation['risk_level'],
            risk_score=explanation['risk_score'],
            explanation=explanation['explanation'],
            concerning_factors=explanation['concerning_factors'],
            recommendations=explanation['recommendations'],
            global_feature_importance=explanation['global_feature_importance']
        )
    except Exception as e:
        logger.error(f"❌ Explanation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Explanation failed: {str(e)}")

# ==================== RAG GUIDANCE ENDPOINT ====================

@router.post("/guidance")   # no response_model — avoids Pydantic re-validating sources as List[str]
async def get_guidance(query: GuidanceQuery):
    """Get AI-powered guidance using RAG + Groq"""
    try:
        logger.info(f"📥 Received RAG guidance query: '{query.query}'")
        generator = get_generator(use_groq=True)
        result = generator.generate_guidance(
            query=query.query,
            user_context=query.context or {}
        )
        logger.info(f"📤 RAG response method: {result['generation_method']}")

        # Safely convert sources to plain strings regardless of what generator returns
        raw_sources = result.get('sources', [])
        sources_list = []
        for s in raw_sources:
            if isinstance(s, dict):
                sources_list.append(s.get('content', s.get('text', str(s))))
            elif isinstance(s, str):
                sources_list.append(s)
            else:
                sources_list.append(str(s))

        # Return plain dict — FastAPI serialises it as JSON without Pydantic re-validation
        return {
            "query": result.get('query', query.query),
            "response": result.get('guidance', result.get('response', '')),
            "generation_method": result.get('generation_method', 'groq_ai'),
            "sources": sources_list
        }

    except Exception as e:
        logger.error(f"❌ RAG guidance failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "query": query.query,
            "response": "I'm here to help with wellness guidance. Please try asking about stress management, sleep improvement, or work-life balance.",
            "generation_method": "fallback",
            "sources": []
        }

# ==================== DATABASE ENDPOINTS ====================

# ✅ FIX: Accept input_data and prediction as a single JSON body dict
#    instead of two separate Pydantic body params (which FastAPI can't
#    distinguish without embed=True or a wrapper model).
class SaveAssessmentBody(BurnoutInput):
    pass

@router.post("/assessment/save")
async def save_assessment(
    payload: Dict = Body(...),
    user_id: Optional[str] = None
):
    """
    Save assessment to database.
    Body: { "input_data": {...}, "prediction": {...} }
    Query param: user_id
    """
    try:
        input_data = payload.get("input_data", {})
        prediction = payload.get("prediction", {})
        db = get_db()
        user = db.get_or_create_user(user_id)
        assessment = db.save_assessment(
            user_id=user.user_id,
            input_data=input_data,
            prediction=prediction
        )
        return {
            "status": "success",
            "message": "Assessment saved successfully",
            "user_id": user.user_id,
            "assessment_id": assessment.id
        }
    except Exception as e:
        logger.error(f"Failed to save assessment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{user_id}")
async def get_history(user_id: str, limit: int = 10):
    try:
        db = get_db()
        try:
            db.session.rollback()  # recover from any prior failed transaction
        except Exception:
            pass
        history = db.get_user_history(user_id, limit)
        stats = db.get_statistics(user_id)
        return {"user_id": user_id, "history": history, "statistics": stats}
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trend/{user_id}")
async def get_trend(user_id: str, days: int = 30):
    try:
        db = get_db()
        trend = db.get_risk_trend(user_id, days)
        return {"user_id": user_id, "days": days, "trend": trend}
    except Exception as e:
        logger.error(f"Failed to get trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/user/create")
async def create_user(name: Optional[str] = None, email: Optional[str] = None):
    try:
        db = get_db()
        user = db.create_user(name, email)
        return {
            "status": "success",
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/{user_id}")
async def get_user_info(user_id: str):
    try:
        db = get_db()
        user = db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/{user_id}")
async def get_user_stats(user_id: str):
    try:
        db = get_db()
        stats = db.get_statistics(user_id)
        return {"user_id": user_id, "statistics": stats}
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== EMAIL NOTIFICATION ENDPOINTS ====================
@router.post("/user/subscribe")
async def subscribe_user(
    user_id: str,
    email: str,
    name: str = None,
    receive_weekly: bool = True,
    receive_alerts: bool = True
):
    try:
        db = get_db()

        # Clear any failed transaction
        try:
            db.session.rollback()
        except Exception:
            pass

        user = db.get_user(user_id)

        # ✅ If user does not exist → create (first login case)
        if not user:
            user = db.create_user(name, email)

        else:
            # ✅ RULE 1: user must use same login email
            if user.email and user.email != email:
                raise HTTPException(
                    status_code=400,
                    detail="You must use your login email only"
                )

            # ✅ RULE 2: prevent duplicate email across users
            existing_user = db.session.query(type(user)).filter_by(email=email).first()
            if existing_user:
                if existing_user.user_id.strip().lower() != user_id.strip().lower():
                  raise HTTPException(
                    status_code=400,
                    detail="Email already used by another user"
                )

            # ✅ Only set email if empty (do NOT overwrite)
            if not user.email:
                user.email = email

            if name:
                user.name = name

            db.session.commit()

        # ================= SAVE SUBSCRIPTION =================
        subscription_key = f"sub_{user_id}"
        subscriptions = {}

        try:
            with open('data/subscriptions.json', 'r') as f:
                subscriptions = json.load(f)
        except Exception:
            pass

        subscriptions[subscription_key] = {
            'user_id': user_id,
            'email': user.email,  # ✅ ALWAYS use DB email
            'receive_weekly': receive_weekly,
            'receive_alerts': receive_alerts,
            'subscribed_at': datetime.now().isoformat()
        }

        import os
        os.makedirs('data', exist_ok=True)

        with open('data/subscriptions.json', 'w') as f:
            json.dump(subscriptions, f, indent=4)

        return {
            "status": "success",
            "message": "Subscribed successfully",
            "user_id": user_id,
            "email": user.email
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to subscribe: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# @router.post("/user/subscribe")
# async def subscribe_user(
#     user_id: str,
#     email: str,
#     name: str = None,
#     receive_weekly: bool = True,
#     receive_alerts: bool = True
# ):
#     try:
#         db = get_db()
#         try:
#             db.session.rollback()  # clear any prior failed transaction
#         except Exception:
#             pass
#         user = db.get_user(user_id)
#         if not user:
#             user = db.create_user(name, email)
#         else:
#             # Only update email if it actually changed AND isn't already taken
#             existing_with_email = db.session.execute(
#                 db.session.query(type(user)).filter_by(email=email)
#             ).scalars().first() if hasattr(db.session, 'query') else None
#             try:
#                 if user.email != email:
#                     user.email = email
#                 if name and user.name != name:
#                     user.name = name
#                 db.session.commit()
#             except Exception as commit_err:
#                 db.session.rollback()
#                 logger.warning(f"Could not update user email (may already exist): {commit_err}")

#         subscription_key = f"sub_{user_id}"
#         subscriptions = {}
#         try:
#             with open('data/subscriptions.json', 'r') as f:
#                 subscriptions = json.load(f)
#         except Exception:
#             pass

#         subscriptions[subscription_key] = {
#             'user_id': user_id,
#             'email': email,
#             'receive_weekly': receive_weekly,
#             'receive_alerts': receive_alerts,
#             'subscribed_at': datetime.now().isoformat()
#         }

#         import os
#         os.makedirs('data', exist_ok=True)
#         with open('data/subscriptions.json', 'w') as f:
#             json.dump(subscriptions, f)

#         return {
#             "status": "success",
#             "message": "Subscribed successfully",
#             "user_id": user_id,
#             "email": email,
#             "receive_weekly": receive_weekly,
#             "receive_alerts": receive_alerts
#         }
#     except Exception as e:
#         logger.error(f"Failed to subscribe: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

@router.post("/send/weekly-report")
async def send_weekly_report_to_user(user_id: str):
    try:
        from src.services.email_service import get_email_service
        email_service = get_email_service()
        success = email_service.send_weekly_report(user_id)
        return {
            "status": "success" if success else "failed",
            "message": "Weekly report sent" if success else "Failed to send report"
        }
    except Exception as e:
        logger.error(f"Failed to send report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ✅ FIX: Accept body as JSON dict instead of query params + Dict mix
class AlertPayload(Dict):
    pass

@router.post("/send/alert")
async def send_high_risk_alert(payload: Dict = Body(...)):
    """
    Send high risk alert.
    Body: { "user_id": "...", "assessment_data": {...}, "prediction": {...} }
    """
    try:
        user_id = payload.get("user_id")
        assessment_data = payload.get("assessment_data", {})
        prediction = payload.get("prediction", {})
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        from src.services.email_service import get_email_service
        email_service = get_email_service()
        success = email_service.send_high_risk_alert(user_id, assessment_data, prediction)
        return {
            "status": "success" if success else "failed",
            "message": "Alert sent" if success else "Failed to send alert"
        }
    except Exception as e:
        logger.error(f"Failed to send alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# ==================== AUTHENTICATION ENDPOINTS ====================
from src.database.models import User  # ✅ ADD THIS IMPORT

@router.post("/auth/signup")
async def signup(user: UserSignup):
    try:
        db = get_db()

        # ✅ FIXED QUERY
        existing_user = db.session.query(User).filter_by(email=user.email).first()

        if existing_user:
            raise HTTPException(status_code=400, detail="Email already exists")

        new_user = db.create_user(user.name, user.email)

        # ✅ STORE PASSWORD
        new_user.password = user.password

        db.session.commit()

        return {
            "status": "success",
            "user_id": new_user.user_id,
            "email": new_user.email
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/auth/login")
async def login(user: UserLogin):
    try:
        db = get_db()

        # ✅ FIXED QUERY
        db_user = db.session.query(User).filter_by(email=user.email).first()

        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        if db_user.password != user.password:
            raise HTTPException(status_code=401, detail="Invalid password")

        return {
            "status": "success",
            "user_id": db_user.user_id,
            "email": db_user.email,
            "name": db_user.name
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset_password")
async def reset_password(payload: dict):
    db = get_db()

    email = payload.get("email")
    password = payload.get("password")

    user = db.session.query(User).filter_by(email=email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password = password
    db.session.commit()

    return {"status": "success"}
__all__ = ['router']