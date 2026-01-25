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
    
    # SF.gov Open Data API
    SF_DATA_API_BASE = "https://data.sfgov.org/resource"
    SF_DATA_APP_TOKEN = os.getenv("SF_DATA_APP_TOKEN", "")
    
    # Nemotron/OpenAI Configuration
    NEMOTRON_BASE_URL = os.getenv("NEMOTRON_BASE_URL", "https://integrate.api.nvidia.com/v1")
    NEMOTRON_API_KEY = os.getenv("NEMOTRON_API_KEY", "")
    NEMOTRON_MODEL = os.getenv("NEMOTRON_MODEL", "nvidia/nemotron-3-nano-30b-a3b")
    
    # Data sources
    BUSINESS_LICENSE_DATASET = "rqzj-sfat"  # SF Business Registry
    PERMITS_DATASET = "p4e4-5k3y"  # Building Permits
    COMPLAINTS_DATASET = "ktji-gkfc"  # Code Enforcement Complaints
    
    # ML Model settings
    RISK_MODEL_VERSION = "v1.0"
    RISK_THRESHOLD_HIGH = 0.7
    RISK_THRESHOLD_MEDIUM = 0.4
    
    # Streamlit settings
    STREAMLIT_TITLE = "SF Small Business Intelligence Platform"
    STREAMLIT_PAGE_ICON = "🏢"
    
    # Agent Workflow settings
    AGENT_SEARCH_QUERIES_COUNT = 5
    AGENT_MAX_SOURCES_PER_QUERY = 10
    AGENT_SCRAPE_DELAY_SECONDS = 2
    AGENT_PAGE_TIMEOUT_SECONDS = 30
    AGENT_MAX_CONTENT_LENGTH = 5000
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.MODELS_DIR.mkdir(parents=True, exist_ok=True)
