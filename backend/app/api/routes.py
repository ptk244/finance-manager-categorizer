"""
API routes for the Finance Manager Categorizer
"""
import structlog
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from datetime import datetime

from app.models.responses import (
    HealthResponse, UploadResponse, CategorizationResponse,
    InsightsResponse, SessionStatusResponse, SupportedFormatsResponse,
    TransactionListResponse, CategorizedTransactionListResponse,
    ResetSessionResponse, ErrorResponse
)
from app.services.transaction_service import TransactionService
from app.services.session_manager import SessionManager
from app.config import get_settings

logger = structlog.get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["Finance Manager"])

# Initialize services
transaction_service = TransactionService()
session_manager = SessionManager()
settings = get_settings()


def get_transaction_service() -> TransactionService:
    """Dependency to get transaction service"""
    return transaction_service


def get_session_manager() -> SessionManager:
    """Dependency to get session manager"""
    return session_manager


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        return HealthResponse(
            status="healthy",
            service="Finance Manager API",
            version=settings.app_version,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=500, detail="Service unhealthy")


@router.post("/upload-statement", response_model=UploadResponse)
async def upload_bank_statement(
    file: UploadFile = File(...),
    service: TransactionService = Depends(get_transaction_service),
    session: SessionManager = Depends(get_session_manager)
):
    """
    Upload and process bank statement file (CSV, Excel, or PDF)
    """
    try:
        logger.info("Received file upload", filename=file.filename, content_type=file.content_type)
        
        # Validate file
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        # Check file extension
        file_ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if file_ext not in settings.allowed_file_types:
            raise HTTPException(
                status_code=422, 
                detail=f"Unsupported file type. Allowed: {', '.join(settings.allowed_file_types)}"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Check file size
        if len(file_content) > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.max_file_size_bytes} bytes"
            )
        
        # Process file
        result = await service.process_uploaded_file(file_content, file.filename)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        # Store in session
        session.store_transactions(
            result["transactions"],
            result.get("file_info", {}),
        )
        
        return UploadResponse(
            success=True,
            message=result["message"],
            transactions=result["transactions"],
            total_transactions=result["total_transactions"],
            file_info=result.get("file_info")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("File upload failed", filename=file.filename if file else "unknown", error=str(e))
        raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")


@router.get("/categorize-transactions", response_model=CategorizationResponse)
async def categorize_transactions(
    service: TransactionService = Depends(get_transaction_service),
    session: SessionManager = Depends(get_session_manager)
):
    """
    Categorize previously uploaded transactions using AI agents
    """
    try:
        logger.info("Starting transaction categorization")
        
        result = await service.categorize_transactions()
        
        if result["success"]:
            # Store categorized data in session
            session.store_categorized_transactions(
                result["categorized_transactions"],
                result["category_summary"]
            )
        
        return CategorizationResponse(
            success=result["success"],
            message=result["message"],
            categorized_transactions=result["categorized_transactions"],
            category_summary=result["category_summary"],
            total_amount=result["total_amount"],
            processing_info=result.get("processing_info")
        )
        
    except Exception as e:
        logger.error("Transaction categorization failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Categorization failed: {str(e)}")


@router.get("/generate-insights", response_model=InsightsResponse)
async def generate_insights(
    service: TransactionService = Depends(get_transaction_service),
    session: SessionManager = Depends(get_session_manager)
):
    """
    Generate comprehensive financial insights from categorized transactions
    """
    try:
        logger.info("Starting insights generation")
        
        result = await service.generate_insights()
        
        if not result["success"]:
            return InsightsResponse(
                success=False,
                message=result["message"],
                insights={}
            )
        
        # Store insights in session
        session.store_insights(result["insights"])
        
        return InsightsResponse(
            success=True,
            message=result["message"],
            insights=result["insights"]
        )
        
    except Exception as e:
        logger.error("Insights generation failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Insights generation failed: {str(e)}")


@router.get("/session-status", response_model=SessionStatusResponse)
async def get_session_status(
    service: TransactionService = Depends(get_transaction_service),
    session: SessionManager = Depends(get_session_manager)
):
    """
    Get current session status and processing state
    """
    try:
        status = service.get_session_status()
        session_status = session.get_session_status()
        
        # Combine both status sources
        combined_status = {**status, **session_status}
        
        return SessionStatusResponse(
            success=True,
            message="Session status retrieved successfully",
            status=combined_status
        )
        
    except Exception as e:
        logger.error("Session status retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")


@router.post("/reset-session", response_model=ResetSessionResponse)
async def reset_session(
    service: TransactionService = Depends(get_transaction_service),
    session: SessionManager = Depends(get_session_manager)
):
    """
    Reset current session and clear all data
    """
    try:
        logger.info("Resetting session")
        
        # Reset service state
        service_result = service.reset_session()
        
        # Reset session manager state
        session.reset_session()
        
        return ResetSessionResponse(
            success=True,
            message="Session reset successfully"
        )
        
    except Exception as e:
        logger.error("Session reset failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Session reset failed: {str(e)}")


@router.get("/supported-formats", response_model=SupportedFormatsResponse)
async def get_supported_formats():
    """
    Get supported file formats and constraints
    """
    try:
        return SupportedFormatsResponse(
            success=True,
            supported_formats=settings.allowed_file_types,
            max_file_size_mb=settings.max_file_size_mb
        )
    except Exception as e:
        logger.error("Failed to get supported formats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve supported formats")


# Debug and utility endpoints
@router.get("/current-transactions", response_model=TransactionListResponse)
async def get_current_transactions(
    service: TransactionService = Depends(get_transaction_service)
):
    """
    Get currently loaded transactions (debug endpoint)
    """
    try:
        transactions = service.get_current_transactions()
        
        return TransactionListResponse(
            success=True,
            transactions=transactions,
            total_count=len(transactions),
            metadata={
                "endpoint": "debug",
                "description": "Currently loaded transactions"
            }
        )
        
    except Exception as e:
        logger.error("Failed to get current transactions", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve transactions: {str(e)}")


@router.get("/current-categorized-data", response_model=CategorizedTransactionListResponse)
async def get_current_categorized_data(
    service: TransactionService = Depends(get_transaction_service)
):
    """
    Get currently categorized transaction data (debug endpoint)
    """
    try:
        categorized_transactions = service.get_categorized_transactions()
        category_summary = service.get_category_summary()
        
        return CategorizedTransactionListResponse(
            success=True,
            categorized_transactions=categorized_transactions,
            total_count=len(categorized_transactions),
            metadata={
                "endpoint": "debug",
                "description": "Currently categorized transactions",
                "categories": list(category_summary.keys()),
                "category_count": len(category_summary)
            }
        )
        
    except Exception as e:
        logger.error("Failed to get categorized data", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve categorized data: {str(e)}")


@router.post("/correct-transaction")
async def correct_transaction_category(
    transaction_index: int,
    correct_category: str,
    correct_subcategory: Optional[str] = None,
    service: TransactionService = Depends(get_transaction_service),
    session: SessionManager = Depends(get_session_manager)
):
    """
    Correct a transaction's category and enable AI learning
    """
    try:
        logger.info("Handling user correction", 
                   transaction_index=transaction_index,
                   correct_category=correct_category)
        
        # Get original category for recording
        categorized_transactions = service.get_categorized_transactions()
        if transaction_index >= len(categorized_transactions):
            raise HTTPException(status_code=400, detail="Invalid transaction index")
        
        original_category = categorized_transactions[transaction_index].category
        
        # Apply correction
        result = await service.handle_user_correction(
            transaction_index,
            correct_category,
            correct_subcategory
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        # Record correction in session
        session.record_user_correction(
            transaction_index,
            original_category,
            correct_category,
            correct_subcategory
        )
        
        return JSONResponse(content={
            "success": True,
            "message": "Transaction category corrected and learned",
            "learning_result": result.get("learning_result", {}),
            "updated_transaction": result.get("updated_transaction", {})
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Transaction correction failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Correction failed: {str(e)}")


@router.get("/processing-history")
async def get_processing_history(
    session: SessionManager = Depends(get_session_manager)
):
    """
    Get session processing history
    """
    try:
        history = session.get_processing_history()
        
        return JSONResponse(content={
            "success": True,
            "processing_history": history,
            "total_events": len(history)
        })
        
    except Exception as e:
        logger.error("Failed to get processing history", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")


@router.get("/user-corrections")
async def get_user_corrections(
    session: SessionManager = Depends(get_session_manager)
):
    """
    Get user corrections history
    """
    try:
        corrections = session.get_user_corrections()
        
        return JSONResponse(content={
            "success": True,
            "user_corrections": corrections,
            "total_corrections": len(corrections)
        })
        
    except Exception as e:
        logger.error("Failed to get user corrections", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve corrections: {str(e)}")


@router.get("/service-stats")
async def get_service_stats(
    service: TransactionService = Depends(get_transaction_service),
    session: SessionManager = Depends(get_session_manager)
):
    """
    Get comprehensive service statistics
    """
    try:
        service_stats = service.get_service_stats()
        session_stats = session.get_session_summary()
        
        return JSONResponse(content={
            "success": True,
            "service_stats": service_stats,
            "session_stats": session_stats,
            "api_info": {
                "version": settings.app_version,
                "supported_formats": settings.allowed_file_types,
                "max_file_size_mb": settings.max_file_size_mb
            }
        })
        
    except Exception as e:
        logger.error("Failed to get service stats", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {str(e)}")


# Root endpoint
@router.get("/")
async def root():
    """Root endpoint with API information"""
    return JSONResponse(content={
        "service": "Finance Manager Categorizer API",
        "version": settings.app_version,
        "description": "AI-powered transaction categorization and financial insights",
        "features": [
            "Multi-format file processing (CSV, Excel, PDF)",
            "AI-powered transaction categorization using Agno + Gemini",
            "Financial insights and recommendations",
            "User correction learning",
            "Team-based AI agents",
            "Indian bank statement support"
        ],
        "endpoints": {
            "health": "/api/v1/health",
            "upload": "/api/v1/upload-statement",
            "categorize": "/api/v1/categorize-transactions",
            "insights": "/api/v1/generate-insights",
            "status": "/api/v1/session-status",
            "reset": "/api/v1/reset-session",
            "formats": "/api/v1/supported-formats"
        },
        "ai_agents": {
            "categorization_agent": "Gemini Pro for high-accuracy categorization",
            "insights_agent": "Gemini Flash for fast insights generation",
            "team_coordination": "Agno 2.0.5 team management"
        }
    })
