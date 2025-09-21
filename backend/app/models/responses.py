"""
API response models
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from .transaction import Transaction, CategorizedTransaction
from .insights import FinancialInsights, CategorySummary


class BaseResponse(BaseModel):
    """Base response model"""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="API health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="API version")
    timestamp: Optional[str] = Field(None, description="Response timestamp")


class UploadResponse(BaseResponse):
    """File upload response"""
    transactions: List[Transaction] = Field(default=[], description="Extracted transactions")
    total_transactions: int = Field(0, description="Total number of transactions")
    file_info: Optional[Dict[str, Any]] = Field(None, description="File processing information")


class CategorizationResponse(BaseResponse):
    """Transaction categorization response"""
    categorized_transactions: List[CategorizedTransaction] = Field(
        default=[], 
        description="Categorized transactions"
    )
    category_summary: Dict[str, CategorySummary] = Field(
        default={}, 
        description="Summary by category"
    )
    total_amount: float = Field(0.0, description="Total transaction amount")
    processing_info: Optional[Dict[str, Any]] = Field(None, description="Processing metadata")


class InsightsResponse(BaseResponse):
    """Financial insights response"""
    insights: FinancialInsights = Field(..., description="Generated financial insights")


class SessionStatus(BaseModel):
    """Current session status"""
    has_transactions: bool = Field(False, description="Whether transactions are loaded")
    has_categorized_data: bool = Field(False, description="Whether data is categorized")
    transaction_count: int = Field(0, description="Number of transactions")
    ready_for_categorization: bool = Field(False, description="Ready for categorization")
    ready_for_insights: bool = Field(False, description="Ready for insights generation")
    last_upload_time: Optional[str] = Field(None, description="Last file upload timestamp")
    last_categorization_time: Optional[str] = Field(None, description="Last categorization timestamp")


class SessionStatusResponse(BaseResponse):
    """Session status response"""
    status: SessionStatus = Field(..., description="Current session status")


class ErrorResponse(BaseModel):
    """Error response model"""
    error: bool = Field(True, description="Indicates an error occurred")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    error_code: Optional[str] = Field(None, description="Specific error code")


class FileValidationResponse(BaseModel):
    """File validation response"""
    valid: bool = Field(..., description="Whether file is valid")
    file_type: Optional[str] = Field(None, description="Detected file type")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    errors: List[str] = Field(default=[], description="Validation errors")
    warnings: List[str] = Field(default=[], description="Validation warnings")


class SupportedFormatsResponse(BaseModel):
    """Supported file formats response"""
    success: bool = Field(True)
    supported_formats: List[str] = Field(..., description="List of supported file formats")
    max_file_size_mb: float = Field(..., description="Maximum file size in MB")


class ProcessingStatusResponse(BaseModel):
    """Processing status response"""
    status: str = Field(..., description="Current processing status")
    progress: Optional[float] = Field(None, description="Processing progress (0-100)")
    estimated_time_remaining: Optional[int] = Field(None, description="Estimated time remaining in seconds")
    current_step: Optional[str] = Field(None, description="Current processing step")


class TransactionListResponse(BaseModel):
    """Response for transaction listing endpoints"""
    success: bool = Field(True)
    transactions: List[Transaction] = Field(..., description="List of transactions")
    total_count: int = Field(..., description="Total number of transactions")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class CategorizedTransactionListResponse(BaseModel):
    """Response for categorized transaction listing"""
    success: bool = Field(True)
    categorized_transactions: List[CategorizedTransaction] = Field(..., description="List of categorized transactions")
    total_count: int = Field(..., description="Total number of transactions")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ResetSessionResponse(BaseResponse):
    """Session reset response"""
    pass  # Inherits from BaseResponse


class ValidationError(BaseModel):
    """Validation error details"""
    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Validation error message")
    value: Optional[Any] = Field(None, description="Value that failed validation")


class ValidationErrorResponse(BaseModel):
    """Response for validation errors"""
    error: bool = Field(True)
    message: str = Field("Validation error")
    validation_errors: List[ValidationError] = Field(..., description="List of validation errors")