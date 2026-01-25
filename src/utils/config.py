"""
Configuration management
"""

import os
from pathlib import Path

class Config:
    """Configuration settings for the SF Business Intelligence Platform"""
    
    # Project paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    RAW_DATA_DIR = DATA_DIR / "raw"
    PROCESSED_DATA_DIR = DATA_DIR / "processed"
    MODELS_DIR = DATA_DIR / "models"
    
    # SF.gov Open Data API (Socrata SODA v2.1 resource endpoint)
    SF_DATA_API_BASE = "https://data.sfgov.org/resource"
    SF_DATA_APP_TOKEN = os.getenv("SF_DATA_APP_TOKEN", "")
    
    # Nemotron/OpenAI Configuration
    NEMOTRON_BASE_URL = os.getenv("NEMOTRON_BASE_URL", "http://localhost:8000/v1")
    NEMOTRON_API_KEY = os.getenv("NEMOTRON_API_KEY", "local-nemotron-key")
    NEMOTRON_MODEL = os.getenv("NEMOTRON_MODEL", "nvidia/nemotron-4-340b-instruct")
    
    # Data sources (Socrata dataset identifiers)
    BUSINESS_LICENSE_DATASET = "g8m3-pdis"  # Registered Business Locations - San Francisco
    PERMITS_DATASET = "i98e-djp9"  # Building Permits
    COMPLAINTS_DATASET = "vw6y-z8j6"  # 311 Cases (includes code-enforcement complaints)
    
    # ML Model settings
    RISK_MODEL_VERSION = "v1.0"
    RISK_THRESHOLD_HIGH = 0.7
    RISK_THRESHOLD_MEDIUM = 0.4
    
    # Streamlit settings
    STREAMLIT_TITLE = "SF Small Business Intelligence Platform"
    STREAMLIT_PAGE_ICON = "🏢"
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.MODELS_DIR.mkdir(parents=True, exist_ok=True)
