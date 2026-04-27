import numpy as np
import pandas as pd
import joblib
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.config.settings import BURNOUT_MODEL_PATH, SCALER_PATH, ENCODER_PATH, FEATURES
from src.data_pipeline.preprocessor import DataPreprocessor

class BurnoutPredictor:
    def __init__(self):
        self.model = None
        self.preprocessor = DataPreprocessor()
        self.load_models()
    
    def load_models(self):
        """Load trained model, scaler, and encoder"""
        try:
            # Load model
            if BURNOUT_MODEL_PATH.exists():
                self.model = joblib.load(BURNOUT_MODEL_PATH)
                print(f"✅ Model loaded from {BURNOUT_MODEL_PATH}")
            else:
                raise FileNotFoundError(f"Model not found at {BURNOUT_MODEL_PATH}")
            
            # Load scaler (already loaded in preprocessor)
            if SCALER_PATH.exists():
                self.preprocessor.scaler = joblib.load(SCALER_PATH)
                print(f"✅ Scaler loaded from {SCALER_PATH}")
            
            # Load encoder
            if ENCODER_PATH.exists():
                self.preprocessor.label_encoder = joblib.load(ENCODER_PATH)
                print(f"✅ Encoder loaded from {ENCODER_PATH}")
                
        except Exception as e:
            print(f"❌ Error loading models: {e}")
            raise
    def predict(self, input_data):

            X_scaled = self.preprocessor.process_prediction_data(input_data)
            prediction_proba = self.model.predict_proba(X_scaled)[0]
            classes = self.preprocessor.label_encoder.classes_

            probs = {cls: float(prediction_proba[i]) for i, cls in enumerate(classes)}

            # -------------------------------
            # ✅ NORMALIZED SCORING (0–100 SAFE)
            # -------------------------------
            sleep = input_data['sleep_hours'] / 10
            stress = input_data['stress_level'] / 10
            work = input_data['workload_hours'] / 12
            screen = input_data['screen_time'] / 12
            activity = input_data['physical_activity'] / 60
            social = input_data['social_interaction'] / 5
            meal = input_data['meal_quality'] / 10
            productivity = input_data['productivity_score'] / 10

            # Convert to risk contributions
            score = (
                (1 - sleep) * 15 +
                stress * 20 +
                work * 15 +
                screen * 10 +
                (1 - activity) * 10 +
                (1 - social) * 10 +
                (1 - meal) * 10 +
                (1 - productivity) * 10
            )

            # Already scaled properly → no overflow
            risk_score = round(score, 2)

            # -------------------------------
            # ✅ CLEAN THRESHOLDS
            # -------------------------------
            if risk_score < 35:
                risk_level = "Low"
            elif risk_score < 65:
                risk_level = "Medium"
            else:
                risk_level = "High"

            return {
                'risk_level': risk_level,
                'risk_score': float(risk_score),
                'confidence': float(max(prediction_proba)),
                'all_probabilities': probs
            }

    def predict_batch(self, input_dataframe):
        """Predict for multiple inputs"""
        X_scaled = self.preprocessor.process_prediction_data(input_dataframe)
        predictions = self.model.predict(X_scaled)
        probabilities = self.model.predict_proba(X_scaled)
        
        results = []
        for pred, prob in zip(predictions, probabilities):

            classes = self.preprocessor.label_encoder.classes_

            probs = {cls: float(p) for cls, p in zip(classes, prob)}

            weights = {
                "Low": 30,
                "Medium": 60,
                "High": 90
            }

            risk_score = sum(probs[cls] * weights[cls] for cls in probs)

            if risk_score < 40:
                risk_level = "Low"
            elif risk_score < 70:
                risk_level = "Medium"
            else:
                risk_level = "High"

            results.append({
                'risk_level': risk_level,
                'risk_score': float(round(risk_score, 2)),
                'confidence': float(max(prob)),
                'probabilities': probs
            })

# Test the predictor
if __name__ == "__main__":
    # Test with sample data
    predictor = BurnoutPredictor()
    
    test_input = {
        'sleep_hours': 6.5,
        'workload_hours': 9,
        'stress_level': 7,
        'screen_time': 8,
        'physical_activity': 20,
        'social_interaction': 1.5,
        'meal_quality': 6,
        'productivity_score': 6
    }
    
    result = predictor.predict(test_input)
    print("\n🔮 Prediction Result:")
    print(f"Risk Level: {result['risk_level']}")
    print(f"Risk Score: {result['risk_score']:.1f}%")
    print(f"Confidence: {result['confidence']:.2%}")
    print("\nAll Probabilities:")
    for risk, prob in result['all_probabilities'].items():
        print(f"  {risk}: {prob:.2%}")