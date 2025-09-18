# models/__init__.py
"""
Pydantic models for Finance Manager Categorizer

This module contains all data models used throughout the application:
- Transaction models
- Bank statement models
- API response models
- Enum definitions for categories and types
"""

__version__ = "1.0.0"

from .transaction import (
    Transaction,
    TransactionType,
    SpendingCategory,
    ProcessedBankStatement,
    CategorySummary,
    InsightsSummary
)
from .response_models import (
    APIResponse,
    FileUploadResponse,
    ProcessingResponse,
    CategorizationResponse,
    InsightsResponse,
    VisualizationResponse,
    HealthCheckResponse
)

__all__ = [
    "Transaction",
    "TransactionType", 
    "SpendingCategory",
    "ProcessedBankStatement",
    "CategorySummary",
    "InsightsSummary",
    "APIResponse",
    "FileUploadResponse",
    "ProcessingResponse",
    "CategorizationResponse",
    "InsightsResponse",
    "VisualizationResponse",
    "HealthCheckResponse"
]
