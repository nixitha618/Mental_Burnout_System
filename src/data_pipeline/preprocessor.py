import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib
from pathlib import Path
import sys
import os

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.config.settings import (
    RAW_DATA_PATH, PROCESSED_DATA_PATH, 
    FEATURES, TARGET, RANDOM_STATE,
    SCALER_PATH, ENCODER_PATH, MODELS_DIR
)

class DataPreprocessor:
    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.features = FEATURES
        
        # Ensure models directory exists
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        
    def load_raw_data(self):
        """Load raw CSV data"""
        print(f"Loading data from {RAW_DATA_PATH}")
        
        # Check if file exists
        if not RAW_DATA_PATH.exists():
            raise FileNotFoundError(f"Data file not found at {RAW_DATA_PATH}. Please ensure the CSV file exists.")
            
        df = pd.read_csv(RAW_DATA_PATH)
        print(f"✅ Loaded {len(df)} samples")
        return df
    
    def clean_data(self, df):
        """Basic data cleaning"""
        print("🔄 Cleaning data...")
        
        # Check for missing values
        initial_len = len(df)
        
        # Check target column for missing values
        if TARGET in df.columns:
            missing_targets = df[TARGET].isna().sum()
            if missing_targets > 0:
                print(f"⚠️ Found {missing_targets} missing values in target column. Dropping these rows.")
                df = df.dropna(subset=[TARGET])
        
        # Drop rows with missing features
        df = df.dropna(subset=self.features)
        
        if len(df) < initial_len:
            print(f"Dropped {initial_len - len(df)} rows with missing values")
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['user_id', 'date'] if 'user_id' in df.columns and 'date' in df.columns else None)
        
        # Ensure numeric columns are properly typed
        numeric_cols = self.features
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Ensure target column is string type
        if TARGET in df.columns:
            df[TARGET] = df[TARGET].astype(str).str.strip()
            # Filter out any invalid values
            valid_targets = ['Low', 'Medium', 'High']
            df = df[df[TARGET].isin(valid_targets)]
            print(f"✅ Target distribution: {df[TARGET].value_counts().to_dict()}")
        
        print(f"✅ Cleaned data: {len(df)} samples remaining")
        return df
    
    def engineer_features(self, df):
        """Create additional features if needed"""
        print("🔄 Engineering features...")
        
        # Example: Create interaction features
        if 'sleep_hours' in df.columns and 'workload_hours' in df.columns:
            df['sleep_to_work_ratio'] = df['sleep_hours'] / (df['workload_hours'] + 0.01)
        
        if 'stress_level' in df.columns and 'physical_activity' in df.columns:
            df['stress_to_activity_ratio'] = df['stress_level'] / (df['physical_activity'] + 0.01)
        
        return df
    
    def prepare_features(self, df, fit_scaler=False):
        """Scale features and prepare for model"""
        print("🔄 Preparing features...")
        X = df[self.features].copy()
        
        if fit_scaler:
            X_scaled = self.scaler.fit_transform(X)
            # Save scaler
            joblib.dump(self.scaler, SCALER_PATH)
            print(f"✅ Scaler saved to {SCALER_PATH}")
        else:
            # Check if scaler exists when not fitting
            if not SCALER_PATH.exists():
                raise FileNotFoundError(f"Scaler not found at {SCALER_PATH}. Please train the model first.")
            X_scaled = self.scaler.transform(X)
        
        return X_scaled
    
    def prepare_target(self, df, fit_encoder=False):
        """Encode target variable"""
        if TARGET not in df.columns:
            return None
            
        print("🔄 Preparing target variable...")
        y = df[TARGET].copy()
        
        if fit_encoder:
            # Fit the encoder
            y_encoded = self.label_encoder.fit_transform(y)
            # Save encoder
            joblib.dump(self.label_encoder, ENCODER_PATH)
            print(f"✅ Encoder saved to {ENCODER_PATH}")
            # Save mapping
            mapping = dict(zip(self.label_encoder.classes_, 
                              self.label_encoder.transform(self.label_encoder.classes_)))
            print(f"✅ Label mapping: {mapping}")
        else:
            # Check if encoder exists when not fitting
            if not ENCODER_PATH.exists():
                raise FileNotFoundError(f"Encoder not found at {ENCODER_PATH}. Please train the model first.")
            y_encoded = self.label_encoder.transform(y)
        
        return y_encoded
    
    def process_training_data(self):
        """Complete preprocessing pipeline for training"""
        try:
            # Load data
            df = self.load_raw_data()
            
            # Clean data
            df = self.clean_data(df)
            
            if len(df) == 0:
                raise ValueError("No valid data remaining after cleaning!")
            
            # Engineer features
            df = self.engineer_features(df)
            
            # Prepare features and target
            X = self.prepare_features(df, fit_scaler=True)
            y = self.prepare_target(df, fit_encoder=True)
            
            # Save processed data as CSV instead of parquet to avoid dependency issues
            PROCESSED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
            processed_df = pd.DataFrame(X, columns=self.features)
            processed_df[TARGET] = y
            
            # Save as CSV instead of parquet
            csv_path = PROCESSED_DATA_PATH.with_suffix('.csv')
            processed_df.to_csv(csv_path, index=False)
            print(f"✅ Processed data saved to {csv_path}")
            
            return X, y
            
        except Exception as e:
            print(f"❌ Error in data preprocessing: {e}")
            raise
    
    def process_prediction_data(self, input_data):
        """Process single prediction input"""
        # Convert dict to DataFrame
        if isinstance(input_data, dict):
            df = pd.DataFrame([input_data])
        else:
            df = input_data
        
        # Ensure all features are present
        for feature in self.features:
            if feature not in df.columns:
                raise ValueError(f"Missing feature: {feature}")
        
        # Select features in correct order
        X = df[self.features].copy()
        
        # Check if scaler exists
        if not SCALER_PATH.exists():
            raise FileNotFoundError(f"Scaler not found at {SCALER_PATH}. Please train the model first.")
        
        # Load scaler if not already loaded
        if not hasattr(self, 'scaler') or self.scaler is None:
            self.scaler = joblib.load(SCALER_PATH)
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        return X_scaled

# Example usage
if __name__ == "__main__":
    print("🔄 Testing data preprocessor...")
    preprocessor = DataPreprocessor()
    X, y = preprocessor.process_training_data()
    print(f"✅ Processed data shape: {X.shape}")
    print(f"✅ Target distribution: {pd.Series(y).value_counts().to_dict()}")