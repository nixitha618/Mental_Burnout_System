import pytest
import sys
from pathlib import Path
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.ml.predictor import BurnoutPredictor
from src.ml.explainer import BurnoutExplainer
from src.data_pipeline.preprocessor import DataPreprocessor

class TestML:
    @pytest.fixture
    def predictor(self):
        return BurnoutPredictor()
    
    @pytest.fixture
    def explainer(self):
        return BurnoutExplainer()
    
    @pytest.fixture
    def sample_input(self):
        return {
            'sleep_hours': 7.0,
            'workload_hours': 8.0,
            'stress_level': 5,
            'screen_time': 6.0,
            'physical_activity': 30,
            'social_interaction': 2.0,
            'meal_quality': 7,
            'productivity_score': 7
        }
    
    def test_predictor_loading(self, predictor):
        assert predictor.model is not None
        assert predictor.preprocessor is not None
    
    def test_prediction(self, predictor, sample_input):
        result = predictor.predict(sample_input)
        assert 'risk_level' in result
        assert 'risk_score' in result
        assert 'confidence' in result
        assert result['risk_level'] in ['Low', 'Medium', 'High']
        assert 0 <= result['risk_score'] <= 100
    
    def test_explainer(self, explainer, sample_input):
        result = explainer.explain_prediction(sample_input)
        assert 'risk_level' in result
        assert 'explanation' in result
        assert 'concerning_factors' in result
        assert 'recommendations' in result
    
    def test_feature_importance(self, explainer):
        importance = explainer.get_feature_importance()
        assert isinstance(importance, dict)
        assert len(importance) > 0

class TestPreprocessor:
    @pytest.fixture
    def preprocessor(self):
        return DataPreprocessor()
    
    def test_feature_list(self, preprocessor):
        assert len(preprocessor.features) == 8
        assert 'sleep_hours' in preprocessor.features
    
    def test_process_prediction_data(self, preprocessor):
        input_data = {
            'sleep_hours': 7.0,
            'workload_hours': 8.0,
            'stress_level': 5,
            'screen_time': 6.0,
            'physical_activity': 30,
            'social_interaction': 2.0,
            'meal_quality': 7,
            'productivity_score': 7
        }
        result = preprocessor.process_prediction_data(input_data)
        assert result.shape[1] == len(preprocessor.features)