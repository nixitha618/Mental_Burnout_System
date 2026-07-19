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
        
        feature_meta = {
            'sleep_hours': {
                'label': 'Sleep Duration',
                'low': 'Try to increase sleep to at least 7 hours per night to support physical and mental recovery.',
                'high': 'Try to limit sleep to at most 9 hours to maintain healthy circadian rhythms.'
            },
            'workload_hours': {
                'label': 'Workload Hours',
                'low': 'Try to increase workload hours to at least 6 hours to stay productive and engaged.',
                'high': 'Try to limit work to at most 8 hours daily. Reducing overtime is essential to prevent chronic fatigue.'
            },
            'stress_level': {
                'label': 'Stress Level',
                'low': 'Your stress levels are extremely low and optimal.',
                'high': 'Try to reduce stress to at most 4/10. Incorporate short relaxation breaks or mindfulness techniques.'
            },
            'screen_time': {
                'label': 'Screen Time',
                'low': 'Your screen time is healthy.',
                'high': 'Try to limit screen time to at most 6 hours to reduce digital eye strain and cognitive load.'
            },
            'physical_activity': {
                'label': 'Physical Activity',
                'low': 'Try to increase physical activity to at least 30 minutes daily to boost mood and energy.',
                'high': 'Try to limit intense physical activity to at most 60 minutes to ensure adequate physical rest.'
            },
            'social_interaction': {
                'label': 'Social Interaction',
                'low': 'Try to increase social interactions to at least 2 hours to prevent isolation and maintain social support.',
                'high': 'Try to limit social interactions to at most 4 hours to allocate enough personal downtime.'
            },
            'meal_quality': {
                'label': 'Meal Quality',
                'low': 'Try to increase meal quality to at least 7/10 by prioritizing balanced nutrition.',
                'high': 'Maintain your healthy meal quality.'
            },
            'productivity_score': {
                'label': 'Productivity Score',
                'low': 'Try to increase productivity to at least 7/10 by setting clear tasks and reducing distractions.',
                'high': 'Your productivity levels are healthy.'
            }
        }
        
        # Define scales for above-optimal calculations
        max_scales = {
            'sleep_hours': 12,
            'workload_hours': 16,
            'stress_level': 10,
            'screen_time': 24,
            'physical_activity': 120,
            'social_interaction': 12,
            'meal_quality': 10,
            'productivity_score': 10
        }
        
        # Find concerning factors
        concerning_factors = []
        for feature in self.features:
            if feature in input_data:
                value = input_data[feature]
                if feature in optimal_ranges:
                    low, high = optimal_ranges[feature]
                    meta = feature_meta.get(feature, {})
                    label = meta.get('label', feature.replace('_', ' ').title())
                    
                    if value < low:
                        # Deviation logic for below-optimal values
                        deviation = low - value
                        max_deviation = low
                        pct = int(min(100, max(0, (deviation / max_deviation) * 100))) if max_deviation > 0 else 50
                        
                        # Determine impact level based on severity
                        impact = 'high' if pct >= 70 else 'medium' if pct >= 35 else 'low'
                        
                        rec = meta.get('low', f'Try to increase to at least {low}')
                        concerning_factors.append({
                            'feature': feature,
                            'value': value,
                            'issue': f'Below optimal range ({low}-{high})',
                            'recommendation': f'{label}: {rec}',
                            'percentage': pct,
                            'impact_pct': pct,
                            'impact': impact
                        })
                    elif value > high:
                        # Deviation logic for above-optimal values
                        deviation = value - high
                        max_scale = max_scales.get(feature, high * 2)
                        max_deviation = max_scale - high
                        pct = int(min(100, max(0, (deviation / max_deviation) * 100))) if max_deviation > 0 else 50
                        
                        # Determine impact level based on severity
                        impact = 'high' if pct >= 70 else 'medium' if pct >= 35 else 'low'
                        
                        rec = meta.get('high', f'Try to reduce to at most {high}')
                        concerning_factors.append({
                            'feature': feature,
                            'value': value,
                            'issue': f'Above optimal range ({low}-{high})',
                            'recommendation': f'{label}: {rec}',
                            'percentage': pct,
                            'impact_pct': pct,
                            'impact': impact
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
        
        # Compute local feature importance based on deviations
        local_importance = {}
        total_pct = 0
        for feature in self.features:
            factor = next((f for f in concerning_factors if f['feature'] == feature), None)
            if factor:
                local_importance[feature] = float(factor['percentage'])
                total_pct += factor['percentage']
            else:
                local_importance[feature] = 5.0  # small base for healthy metrics
                total_pct += 5.0
                
        if total_pct > 0:
            for feature in local_importance:
                local_importance[feature] = local_importance[feature] / total_pct
        else:
            local_importance = global_importance

        return {
            'risk_level': prediction['risk_level'],
            'risk_score': prediction['risk_score'],
            'concerning_factors': concerning_factors,
            'global_feature_importance': global_importance,
            'local_feature_importance': local_importance,
            'importance': local_importance,
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