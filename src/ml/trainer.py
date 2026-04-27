import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
from pathlib import Path
import sys
import json

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.config.settings import (
    MODELS_DIR, BURNOUT_MODEL_PATH, RANDOM_STATE, 
    TEST_SIZE, MODEL_TYPE, FEATURES, PROCESSED_DATA_PATH
)
from src.data_pipeline.preprocessor import DataPreprocessor

class ModelTrainer:
    def __init__(self, model_type=MODEL_TYPE):
        self.model_type = model_type
        self.model = None
        self.preprocessor = DataPreprocessor()
        self.class_names = None
        
    def get_model(self):
        """Get model based on configuration"""
        if self.model_type == "logistic_regression":
            return LogisticRegression(
                random_state=RANDOM_STATE,
                max_iter=1000,
                multi_class='ovr'
            )
        elif self.model_type == "random_forest":
            return RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=RANDOM_STATE,
                n_jobs=-1
            )
        elif self.model_type == "xgboost":
            return XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=RANDOM_STATE,
                eval_metric='mlogloss'
                # Removed use_label_encoder as it's deprecated
            )
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
    
    def train(self, X, y):
        """Train the model"""
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
        )
        
        # Get class names from encoder
        if hasattr(self.preprocessor.label_encoder, 'classes_'):
            self.class_names = self.preprocessor.label_encoder.classes_
        else:
            # If classes_ not available, try to load from saved encoder
            try:
                encoder_path = Path(__file__).resolve().parent.parent.parent / 'models' / 'label_encoder.pkl'
                if encoder_path.exists():
                    encoder = joblib.load(encoder_path)
                    self.class_names = encoder.classes_
                else:
                    # Fallback to unique values
                    unique_values = np.unique(y)
                    self.class_names = [str(val) for val in unique_values]
            except:
                unique_values = np.unique(y)
                self.class_names = [str(val) for val in unique_values]
        
        # Get and train model
        self.model = self.get_model()
        print(f"\n🚀 Training {self.model_type}...")
        self.model.fit(X_train, y_train)
        
        # Evaluate
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        print(f"\n📊 Training Results:")
        print(f"   Train accuracy: {train_score:.4f}")
        print(f"   Test accuracy: {test_score:.4f}")
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, X, y, cv=5)
        print(f"   Cross-validation scores: {cv_scores}")
        print(f"   CV mean: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
        
        # Detailed metrics
        y_pred = self.model.predict(X_test)
        print("\n📈 Classification Report:")
        print(classification_report(y_test, y_pred, 
                                   target_names=self.class_names,
                                   zero_division=0))
        
        # Confusion Matrix
        cm = confusion_matrix(y_test, y_pred)
        print("\n📊 Confusion Matrix:")
        print(cm)
        
        # Feature importance (if available)
        if hasattr(self.model, 'feature_importances_'):
            importance = self.model.feature_importances_
            print("\n🔍 Feature Importances:")
            for name, imp in zip(FEATURES, importance):
                print(f"   {name}: {imp:.4f}")
        elif hasattr(self.model, 'coef_'):
            importance = np.mean(np.abs(self.model.coef_), axis=0)
            print("\n🔍 Feature Importances (from coefficients):")
            for name, imp in zip(FEATURES, importance):
                print(f"   {name}: {imp:.4f}")
        
        return {
            'train_accuracy': float(train_score),
            'test_accuracy': float(test_score),
            'cv_mean': float(cv_scores.mean()),
            'cv_std': float(cv_scores.std())
        }
    
    def save_model(self):
        """Save trained model"""
        if self.model:
            joblib.dump(self.model, BURNOUT_MODEL_PATH)
            print(f"\n💾 Model saved to {BURNOUT_MODEL_PATH}")
            
            # Save model metadata
            metadata = {
                'model_type': self.model_type,
                'features': FEATURES,
                'random_state': RANDOM_STATE,
                'classes': self.class_names.tolist() if hasattr(self.class_names, 'tolist') else list(self.class_names)
            }
            metadata_path = MODELS_DIR / 'model_metadata.json'
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            print(f"💾 Model metadata saved to {metadata_path}")
    
    def load_model(self):
        """Load trained model"""
        if BURNOUT_MODEL_PATH.exists():
            self.model = joblib.load(BURNOUT_MODEL_PATH)
            print(f"✅ Model loaded from {BURNOUT_MODEL_PATH}")
            
            # Load metadata if available
            metadata_path = MODELS_DIR / 'model_metadata.json'
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                self.class_names = metadata.get('classes', ['High', 'Low', 'Medium'])
            
            return self.model
        else:
            raise FileNotFoundError(f"Model not found at {BURNOUT_MODEL_PATH}")

# Training script
if __name__ == "__main__":
    print("="*50)
    print("🧠 MENTAL BURNOUT EARLY WARNING SYSTEM")
    print("="*50)
    
    try:
        # Prepare data
        print("\n📥 Step 1: Preparing training data...")
        preprocessor = DataPreprocessor()
        X, y = preprocessor.process_training_data()
        print(f"✅ Data prepared: {X.shape[0]} samples, {X.shape[1]} features")
        
        # Get class names
        if hasattr(preprocessor.label_encoder, 'classes_'):
            class_names = preprocessor.label_encoder.classes_
        else:
            # Try to load from saved encoder
            encoder_path = Path(__file__).resolve().parent.parent.parent / 'models' / 'label_encoder.pkl'
            if encoder_path.exists():
                encoder = joblib.load(encoder_path)
                class_names = encoder.classes_
            else:
                class_names = ['High', 'Low', 'Medium']
        
        print(f"✅ Classes: {class_names}")
        
        # Train model
        print("\n📚 Step 2: Training model...")
        trainer = ModelTrainer()
        trainer.class_names = class_names
        metrics = trainer.train(X, y)
        
        # Save model
        print("\n💾 Step 3: Saving model...")
        trainer.save_model()
        
        print("\n" + "="*50)
        print("✅ TRAINING COMPLETED SUCCESSFULLY!")
        print("="*50)
        print(f"\nModel Type: {MODEL_TYPE}")
        print(f"Test Accuracy: {metrics['test_accuracy']:.2%}")
        print(f"Cross-validation: {metrics['cv_mean']:.2%} ± {metrics['cv_std']:.2%}")
        print("\nYou can now start the API with: python -m src.api.main")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure the CSV file exists at data/raw/sample_user_data.csv")
        print("2. Check that the CSV has the correct columns")
        print("3. Run: pip install pyarrow fastparquet")
        import traceback
        traceback.print_exc()