"""
Tools layer for the SF Business Intelligence Platform

This module provides reusable tools for:
- Socrata/SODA API queries (SoQL)
- NIM API interactions (Nemotron)
- NeMo Retriever (embeddings, reranking)
- Schema validation (Pydantic)
"""

from .socrata_client import SocrataClient
from .nim_client import NIMClient
from .schema_validation import validate_schema, ValidationError

__all__ = [
    "SocrataClient",
    "NIMClient", 
    "validate_schema",
    "ValidationError",
]
