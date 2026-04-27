# import os
# from pathlib import Path
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()

# # Project paths
# BASE_DIR = Path(__file__).resolve().parent.parent.parent
# DATA_DIR = BASE_DIR / "data"
# MODELS_DIR = BASE_DIR / "models"
# VECTOR_DB_DIR = DATA_DIR / "vector_db"

# # Data paths
# RAW_DATA_PATH = DATA_DIR / "raw" / "sample_user_data.csv"
# PROCESSED_DATA_PATH = DATA_DIR / "processed" / "training_data.parquet"

# # Model paths
# BURNOUT_MODEL_PATH = MODELS_DIR / "burnout_model.pkl"
# SCALER_PATH = MODELS_DIR / "scaler.pkl"
# ENCODER_PATH = MODELS_DIR / "label_encoder.pkl"

# # ML Model settings
# RANDOM_STATE = 42
# TEST_SIZE = 0.2
# MODEL_TYPE = "xgboost"  # Options: "logistic_regression", "random_forest", "xgboost"

# # API Settings
# API_HOST = os.getenv("API_HOST", "localhost")
# API_PORT = int(os.getenv("API_PORT", 8000))
# DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# # Feature names
# FEATURES = [
#     "sleep_hours",
#     "workload_hours", 
#     "stress_level",
#     "screen_time",
#     "physical_activity",
#     "social_interaction",
#     "meal_quality",
#     "productivity_score"
# ]

# TARGET = "burnout_risk"

# # Risk level mapping
# RISK_LEVELS = ["Low", "Medium", "High"]
# RISK_THRESHOLDS = {
#     "Low": (0, 30),
#     "Medium": (30, 60),
#     "High": (60, 100)
# }


import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
VECTOR_DB_DIR = DATA_DIR / "vector_db"

# Create directories if they don't exist
for directory in [DATA_DIR, MODELS_DIR, VECTOR_DB_DIR, DATA_DIR / "raw", DATA_DIR / "processed"]:
    directory.mkdir(parents=True, exist_ok=True)
    print(f"✅ Directory ensured: {directory}")

# Data paths
RAW_DATA_PATH = DATA_DIR / "raw" / "sample_user_data.csv"
PROCESSED_DATA_PATH = DATA_DIR / "processed" / "training_data.parquet"

# Model paths
BURNOUT_MODEL_PATH = MODELS_DIR / "burnout_model.pkl"
SCALER_PATH = MODELS_DIR / "scaler.pkl"
ENCODER_PATH = MODELS_DIR / "label_encoder.pkl"

# ML Model settings
RANDOM_STATE = 42
TEST_SIZE = 0.2
MODEL_TYPE = "xgboost"  # Options: "logistic_regression", "random_forest", "xgboost"

# API Settings
API_HOST = os.getenv("API_HOST", "localhost")
API_PORT = int(os.getenv("API_PORT", 8000))
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Feature names
FEATURES = [
    "sleep_hours",
    "workload_hours", 
    "stress_level",
    "screen_time",
    "physical_activity",
    "social_interaction",
    "meal_quality",
    "productivity_score"
]

TARGET = "burnout_risk"

# Risk level mapping
RISK_LEVELS = ["Low", "Medium", "High"]
RISK_THRESHOLDS = {
    "Low": (0, 30),
    "Medium": (30, 60),
    "High": (60, 100)
}

print(f"📁 Models directory: {MODELS_DIR}")
print(f"📁 Data directory: {DATA_DIR}")