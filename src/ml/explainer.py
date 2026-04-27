import numpy as np
import pandas as pd
import joblib
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.config.settings import BURNOUT_MODEL_PATH, FEATURES
from src.ml.predictor import BurnoutPredictor

class BurnoutExplainer:
    def __init__(self):
        self.predictor = BurnoutPredictor()
        self.model = self.predictor.model
        self.features = FEATURES
    
    def get_feature_importance(self, input_data=None):
        """Get feature importance for the model"""
        importance_dict = {}
        
        # For tree-based models (Random Forest, XGBoost)
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            for name, imp in zip(self.features, importances):
                importance_dict[name] = float(imp)
        
        # For linear models (Logistic Regression)
        elif hasattr(self.model, 'coef_'):
            importances = np.mean(np.abs(self.model.coef_), axis=0)
            for name, imp in zip(self.features, importances):
                importance_dict[name] = float(imp)
        
        # Sort by importance
        importance_dict = dict(sorted(
            importance_dict.items(), 
            key=lambda x: x[1], 
            reverse=True
        ))
        
        return importance_dict
    
    def explain_prediction(self, input_data):
        """Explain why a particular prediction was made"""
        # Get prediction
        prediction = self.predictor.predict(input_data)
        
        # Get feature importance
        global_importance = self.get_feature_importance()
        
        # For local explanation, we can use the input values
        # and compare with optimal ranges
        optimal_ranges = {
            'sleep_hours': (7, 9),
            'workload_hours': (6, 8),
            'stress_level': (1, 4),
            'screen_time': (4, 6),
            'physical_activity': (30, 60),
            'social_interaction': (2, 4),
            'meal_quality': (7, 10),
            'productivity_score': (7, 10)
        }
        
        # Find concerning factors
        concerning_factors = []
        for feature in self.features:
            if feature in input_data:
                value = input_data[feature]
                if feature in optimal_ranges:
                    low, high = optimal_ranges[feature]
                    if value < low:
                        concerning_factors.append({
                            'feature': feature,
                            'value': value,
                            'issue': f'Below optimal range ({low}-{high})',
                            'recommendation': f'Try to increase to at least {low}'
                        })
                    elif value > high:
                        concerning_factors.append({
                            'feature': feature,
                            'value': value,
                            'issue': f'Above optimal range ({low}-{high})',
                            'recommendation': f'Try to reduce to at most {high}'
                        })
        
        # Sort concerning factors by global importance
        concerning_factors.sort(
            key=lambda x: global_importance.get(x['feature'], 0),
            reverse=True
        )
        
        # Generate explanation text
        if len(concerning_factors) == 0:
            explanation = "All your metrics are within healthy ranges! Keep up the good work!"
        else:
            main_factors = concerning_factors[:3]
            explanation = f"Your {prediction['risk_level']} risk is primarily due to: "
            explanation += ", ".join([f"{f['feature'].replace('_', ' ')} ({f['value']})" 
                                     for f in main_factors])
        
        return {
            'risk_level': prediction['risk_level'],
            'risk_score': prediction['risk_score'],
            'concerning_factors': concerning_factors,
            'global_feature_importance': global_importance,
            'explanation': explanation,
            'recommendations': [f['recommendation'] for f in concerning_factors[:3]]
        }

# Test the explainer
if __name__ == "__main__":
    explainer = BurnoutExplainer()
    
    test_input = {
        'sleep_hours': 5.5,
        'workload_hours': 11,
        'stress_level': 8,
        'screen_time': 10,
        'physical_activity': 15,
        'social_interaction': 0.5,
        'meal_quality': 4,
        'productivity_score': 4
    }
    
    explanation = explainer.explain_prediction(test_input)
    print("\n🔍 Prediction Explanation:")
    print(f"Risk Level: {explanation['risk_level']}")
    print(f"Risk Score: {explanation['risk_score']:.1f}%")
    print(f"\n📝 Explanation: {explanation['explanation']}")
    print("\n⚠️ Concerning Factors:")
    for factor in explanation['concerning_factors']:
        print(f"  • {factor['feature']}: {factor['value']} - {factor['issue']}")
        print(f"    💡 {factor['recommendation']}")