from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from models.transaction import InsightsSummary, ProcessedBankStatement


class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None

class FileUploadResponse(APIResponse):
    data: Optional[Dict[str, Any]] = None

class ProcessingResponse(APIResponse):
    data: Optional[ProcessedBankStatement] = None

class CategorizationResponse(APIResponse):
    data: Optional[ProcessedBankStatement] = None

class InsightsResponse(APIResponse):
    data: Optional[InsightsSummary] = None

class VisualizationResponse(APIResponse):
    data: Optional[Dict[str, Any]] = None

class HealthCheckResponse(BaseModel):
    status: str
    gemini_api_status: str
    agno_version: str
    timestamp: str