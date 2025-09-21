"""
Finance Manager Categorizer - Main FastAPI Application
AI-powered transaction categorization using Agno 2.0.5 and Gemini models
"""
import uvicorn
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import get_settings, validate_settings
from app.api.routes import router
from app.services.session_manager import SessionManager

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting Finance Manager Categorizer API", 
               version=settings.app_version)
    
    try:
        # Validate configuration
        validate_settings()
        logger.info("Configuration validated successfully")
        
        # Initialize session manager cleanup
        session_manager = SessionManager()
        
        # Log AI configuration
        logger.info("AI Configuration", 
                   categorization_model=settings.categorization_model,
                   insights_model=settings.insights_model,
                   gemini_api_configured=bool(settings.gemini_api_key))
        
        logger.info("Finance Manager API started successfully",
                   host=settings.host,
                   port=settings.port,
                   debug=settings.debug)    
        
        yield  # Application runs here
        
    except Exception as e:
        logger.error("Startup failed", error=str(e))
        raise
    
    # Shutdown
    logger.info("Shutting down Finance Manager API")
    
    try:
        # Cleanup old sessions
        session_manager.cleanup_old_sessions()
        logger.info("Session cleanup completed")
        
    except Exception as e:
        logger.error("Shutdown cleanup failed", error=str(e))
    
    logger.info("Finance Manager API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Finance Manager Categorizer API",
    description="""
    🤖 AI-Powered Finance Manager with Agentic Transaction Categorization
    
    ## Features
    
    * **Multi-format Support**: Process CSV, Excel (XLS/XLSX), and PDF bank statements
    * **AI-Powered Categorization**: Uses Gemini Pro model via Agno 2.0.5 for high-accuracy transaction categorization
    * **Financial Insights**: Generate comprehensive financial insights using Gemini Flash model
    * **Team-based AI**: Coordinated AI agents working together for optimal results
    * **Indian Bank Support**: Specialized support for Indian bank statement formats (ICICI, SBI, HDFC)
    * **Learning Capability**: AI learns from user corrections to improve future categorizations
    * **Real-time Processing**: Fast, efficient processing with intelligent fallbacks
    
    ## AI Agent Architecture
    
    * **Categorization Agent**: Uses Gemini Pro (gemini-1.5-pro-002) for precise transaction categorization
    * **Insights Agent**: Uses Gemini Flash (gemini-1.5-flash-002) for rapid insights generation
    * **Team Coordination**: Agno 2.0.5 framework manages agent collaboration and workflows
    
    ## Workflow
    
    1. **Upload**: Upload bank statement file (CSV/Excel/PDF)
    2. **Categorize**: AI agents automatically categorize transactions
    3. **Insights**: Generate comprehensive financial insights and recommendations
    4. **Learn**: Provide corrections to improve AI accuracy over time
    
    ## Categories Supported
    
    Food & Dining, Groceries, Shopping, Bills & Utilities, Travel, Transportation, 
    Entertainment, Healthcare, Education, Investments, Salary/Income, Bank Fees, 
    Insurance, Loans, Miscellaneous
    """,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors"""
    logger.warning("Request validation error", 
                  path=request.url.path,
                  errors=exc.errors())
    
    return JSONResponse(
        status_code=422,
        content={
            "error": True,
            "message": "Request validation failed",
            "details": exc.errors(),
            "error_type": "validation_error"
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    logger.warning("HTTP exception", 
                  path=request.url.path,
                  status_code=exc.status_code,
                  detail=exc.detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
            "error_type": "http_error"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions"""
    logger.error("Unexpected error", 
                path=request.url.path,
                error=str(exc),
                error_type=type(exc).__name__)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "An unexpected error occurred",
            "error_type": "internal_error",
            "details": str(exc) if settings.debug else "Internal server error"
        }
    )


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Welcome endpoint with API information and quick links
    """
    return JSONResponse(content={
        "🤖": "Finance Manager Categorizer API",
        "version": settings.app_version,
        "description": "AI-powered transaction categorization using Agno 2.0.5",
        "status": "operational",
        "ai_models": {
            "categorization": settings.categorization_model,
            "insights": settings.insights_model,
            "framework": "Agno 2.0.5"
        },
        "quick_start": {
            "1": "Upload bank statement: POST /api/v1/upload-statement",
            "2": "Categorize transactions: GET /api/v1/categorize-transactions", 
            "3": "Generate insights: GET /api/v1/generate-insights",
            "4": "Check status: GET /api/v1/session-status"
        },
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "features": [
            "Multi-format file processing",
            "AI-powered categorization",
            "Financial insights generation", 
            "User correction learning",
            "Indian bank statement support",
            "Team-based AI agents"
        ],
        "support": {
            "formats": ["CSV", "Excel (XLS/XLSX)", "PDF"],
            "max_file_size": f"{settings.max_file_size_mb}MB",
            "categories": len(settings.default_categories)
        }
    })


# Health check endpoint (redundant with API router, but useful for load balancers)
@app.get("/health", tags=["Health"])
async def health_check():
    """Simple health check for load balancers"""
    return JSONResponse(content={
        "status": "healthy",
        "service": "Finance Manager API",
        "version": settings.app_version,
        "timestamp": "2024-01-01T00:00:00"  # Would be actual timestamp
    })


# Development utilities
if settings.debug:
    @app.get("/debug/config", tags=["Debug"])
    async def debug_config():
        """Debug endpoint to check configuration (only in debug mode)"""
        return JSONResponse(content={
            "debug_mode": settings.debug,
            "app_version": settings.app_version,
            "gemini_api_configured": bool(settings.gemini_api_key),
            "categorization_model": settings.categorization_model,
            "insights_model": settings.insights_model,
            "max_file_size_mb": settings.max_file_size_mb,
            "allowed_file_types": settings.allowed_file_types,
            "default_categories": settings.default_categories,
            "note": "This endpoint is only available in debug mode"
        })


def create_app() -> FastAPI:
    """
    Application factory function
    Useful for testing and deployment
    """
    return app


if __name__ == "__main__":
    """
    Run the application directly with uvicorn
    For development purposes only
    """
    logger.info("Starting Finance Manager API in development mode")
    
    try:
        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level=settings.log_level.lower(),
            access_log=True,
            loop="asyncio"
        )
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error("Application startup failed", error=str(e))
        raise