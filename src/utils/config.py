"""
Configuration management for SF Business Intelligence Platform

Provides centralized configuration for:
- DataSF (Socrata) dataset endpoints
- Nemotron/NIM API endpoints (DGX Spark)
- ML model settings
- Agent workflow settings
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """Configuration settings for the SF Business Intelligence Platform"""
    
    # Project paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    RAW_DATA_DIR = DATA_DIR / "raw"
    PROCESSED_DATA_DIR = DATA_DIR / "processed"
    MODELS_DIR = PROJECT_ROOT / "models"
    
    # SF.gov Open Data API (Socrata SODA v2.1 resource endpoint)
    SF_DATA_API_BASE = "https://data.sfgov.org/resource"
    SF_DATA_APP_TOKEN = os.getenv("SF_DATA_APP_TOKEN", "")
    
    # Nemotron/NIM Configuration
    # Supports both NVIDIA API (build.nvidia.com) and local DGX Spark
    # For NVIDIA API: set NEMOTRON_BASE_URL="https://integrate.api.nvidia.com/v1"
    # For local NIM: set NEMOTRON_BASE_URL="http://localhost:8000/v1"
    NEMOTRON_BASE_URL = os.getenv("NEMOTRON_BASE_URL", "https://integrate.api.nvidia.com/v1")
    NEMOTRON_API_KEY = os.getenv("NEMOTRON_API_KEY", os.getenv("NVIDIA_API_KEY", ""))
    
    # Available Nemotron models:
    # - nvidia/llama-3.1-nemotron-70b-instruct (recommended for general use)
    # - nvidia/llama-3.1-nemotron-ultra-253b-v1 (highest quality, slower)
    # - nvidia/nemotron-4-340b-instruct (legacy)
    NEMOTRON_MODEL = os.getenv("NEMOTRON_MODEL", "nvidia/llama-3.1-nemotron-70b-instruct")
    
    # NIM Health endpoints (supports both vLLM and NIM formats)
    NIM_HEALTH_READY = "/health"  # vLLM uses /health, NIM uses /v1/health/ready
    NIM_HEALTH_LIVE = "/health"
    NIM_MODELS_ENDPOINT = "/v1/models"
    
    # Optional: NeMo Retriever NIM microservices
    EMBEDDING_NIM_URL = os.getenv("EMBEDDING_NIM_URL", "http://localhost:8001/v1")
    RERANKING_NIM_URL = os.getenv("RERANKING_NIM_URL", "http://localhost:8002/v1")
    
    # ==========================================================================
    # DATASF DATASET IDs (Socrata)
    # All datasets use SoQL query language via SODA API
    # ==========================================================================
    
    # Core datasets (existing)
    BUSINESS_LICENSE_DATASET = "g8m3-pdis"  # Registered Business Locations - San Francisco
    PERMITS_DATASET = "i98e-djp9"  # Building Permits
    COMPLAINTS_DATASET = "vw6y-z8j6"  # 311 Cases (nightly updates ~6am Pacific)
    
    # Code / Building Enforcement
    DBI_COMPLAINTS_DATASET = "gm2e-bten"  # DBI Complaints (All Divisions)
    
    # Public Safety
    SFPD_INCIDENTS_DATASET = "wg3w-h783"  # SFPD Incident Reports (2018-present)
    # Note: SFPD records may be removed for court orders/admin reasons; treat as mutable
    
    # Neighborhood Economic Stress
    EVICTION_NOTICES_DATASET = "5cei-gny5"  # Eviction Notices
    # Note: Historic duplicate row issue (fixed); keep dedupe logic
    
    # Commercial Corridor Stress
    TAXABLE_COMMERCIAL_SPACES_DATASET = "rzkk-54yv"  # Taxable Commercial Spaces
    COMMERCIAL_VACANCY_TAX_DATASET = "iynh-ydf2"  # Commercial Vacancy Tax Status
    # IMPORTANT: Do NOT use filer_name field - contains PII
    
    # Dataset configuration with metadata
    DATASETS: Dict[str, Dict[str, Any]] = {
        "business_registry": {
            "id": "g8m3-pdis",
            "name": "Registered Business Locations",
            "update_frequency": "weekly",
            "geo_enabled": True,
        },
        "permits": {
            "id": "i98e-djp9",
            "name": "Building Permits",
            "update_frequency": "daily",
            "geo_enabled": True,
        },
        "complaints_311": {
            "id": "vw6y-z8j6",
            "name": "311 Cases",
            "update_frequency": "nightly",  # ~6am Pacific
            "geo_enabled": True,
        },
        "dbi_complaints": {
            "id": "gm2e-bten",
            "name": "DBI Complaints (All Divisions)",
            "update_frequency": "weekly",
            "geo_enabled": True,
        },
        "sfpd_incidents": {
            "id": "wg3w-h783",
            "name": "SFPD Incident Reports (2018-present)",
            "update_frequency": "daily",
            "geo_enabled": True,
            "mutable": True,  # Records can be removed
        },
        "evictions": {
            "id": "5cei-gny5",
            "name": "Eviction Notices",
            "update_frequency": "weekly",
            "geo_enabled": False,
            "dedupe_required": True,
        },
        "taxable_commercial_spaces": {
            "id": "rzkk-54yv",
            "name": "Taxable Commercial Spaces",
            "update_frequency": "quarterly",
            "geo_enabled": True,
        },
        "commercial_vacancy_tax": {
            "id": "iynh-ydf2",
            "name": "Commercial Vacancy Tax Status",
            "update_frequency": "annual",
            "geo_enabled": False,
            "pii_fields": ["filer_name"],  # Do NOT use for modeling
        },
    }
    
    # ML Model settings
    RISK_MODEL_VERSION = "v1.0"
    RISK_THRESHOLD_HIGH = 0.7
    RISK_THRESHOLD_MEDIUM = 0.4
    
    # Feature windows (months) for time-based aggregations
    FEATURE_WINDOWS = [3, 6, 12]  # 3-month, 6-month, 12-month rolling windows
    
    # Geo settings
    DEFAULT_SEARCH_RADIUS_METERS = 500  # For spatial queries
    GEOHASH_PRECISION = 7  # ~150m x 150m grid cells
    
    # Streamlit settings
    STREAMLIT_TITLE = "SF Small Business Intelligence Platform"
    STREAMLIT_PAGE_ICON = "🏢"
    
    # ==========================================================================
    # MULTI-AGENT SETTINGS
    # ==========================================================================
    
    # Agent general settings
    AGENT_SEARCH_QUERIES_COUNT = 5
    AGENT_MAX_SOURCES_PER_QUERY = 10
    AGENT_SCRAPE_DELAY_SECONDS = 2
    AGENT_PAGE_TIMEOUT_SECONDS = 30
    AGENT_MAX_CONTENT_LENGTH = 5000
    
    # LLM Agent settings (Nemotron)
    LLM_TEMPERATURE_DETERMINISTIC = 0.1  # For reliable outputs
    LLM_TEMPERATURE_CREATIVE = 0.7  # For scenario generation
    LLM_MAX_TOKENS_EXPLANATION = 1500
    LLM_MAX_TOKENS_STRATEGY = 2500
    LLM_MAX_TOKENS_QA = 500
    
    # Entity resolution settings
    ENTITY_MATCH_CONFIDENCE_THRESHOLD = 0.6  # Below this, require user confirmation
    
    # Data freshness settings (hours)
    DATA_FRESHNESS_THRESHOLDS = {
        "complaints_311": 24,  # Nightly updates
        "permits": 48,
        "sfpd_incidents": 48,
        "business_registry": 168,  # Weekly
        "evictions": 168,
        "dbi_complaints": 168,
    }
    
    # Yutori API Configuration
    YUTORI_API_KEY = os.getenv("YUTORI_API_KEY", "")
    YUTORI_API_BASE = "https://api.yutori.ai"
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_dataset_id(cls, dataset_key: str) -> str:
        """Get Socrata dataset ID by key"""
        if dataset_key in cls.DATASETS:
            return cls.DATASETS[dataset_key]["id"]
        raise ValueError(f"Unknown dataset key: {dataset_key}")
    
    @classmethod
    def get_nim_base_url(cls) -> str:
        """Get the base NIM URL without /v1 suffix"""
        return cls.NEMOTRON_BASE_URL.replace("/v1", "")
