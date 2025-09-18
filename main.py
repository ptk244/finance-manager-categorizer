from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import os

# Import configuration
from config.settings import settings

# Import API routes
from api.routes import upload, categorize, insights

# Import services
from services.gemini_service import gemini_service
from services.agent_team_service import agent_team_service

# Import models
from models.response_models import HealthCheckResponse, APIResponse

# Import logging
from loguru import logger
import sys

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    level=settings.agno_log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Finance Manager Categorizer API")
    
    # Ensure upload directory exists
    os.makedirs(settings.upload_dir, exist_ok=True)
    logger.info(f"Upload directory ready: {settings.upload_dir}")
    
    # Test Gemini API connection
    try:
        gemini_status = await gemini_service.test_connection()
        if gemini_status.get('status') == 'connected':
            logger.info("✅ Gemini API connection successful")
        else:
            logger.warning("⚠️  Gemini API connection failed")
    except Exception as e:
        logger.error(f"❌ Gemini API test failed: {str(e)}")
    
    # Test agent team
    try:
        team_status = await agent_team_service.get_team_status()
        logger.info(f"✅ Agent team ready: {team_status.get('agents_count', 0)} agents")
    except Exception as e:
        logger.error(f"❌ Agent team initialization failed: {str(e)}")
    
    logger.info("🚀 Finance Manager API is ready!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Finance Manager API")
    
    # Cleanup uploaded files (optional)
    # You might want to keep files for a certain period
    logger.info("Cleanup completed")

# Create FastAPI app
app = FastAPI(
    title="Finance Manager Categorizer",
    description="""
    AI-Powered Finance Manager for Bank Statement Analysis
    
    This API provides comprehensive financial analysis capabilities:
    
    ## Features
    * 📄 **Multi-format Support**: Upload CSV, Excel, or PDF bank statements
    * 🤖 **AI Categorization**: Automatic transaction categorization using Gemini AI
    * 📊 **Smart Insights**: Generate actionable financial insights and recommendations
    * 📈 **Interactive Visualizations**: Create comprehensive financial dashboards
    * 🔄 **Multi-Agent System**: Powered by Agno framework with specialized agents
    
    ## Workflow
    1. **Upload** your bank statement file
    2. **Process** and extract transaction data
    3. **Categorize** transactions using AI and rule-based systems
    4. **Generate** insights and recommendations
    5. **Visualize** your financial data with interactive charts
    
    ## Supported File Formats
    * CSV files (.csv)
    * Excel files (.xlsx, .xls)
    * PDF bank statements (.pdf)
    
    ## AI Models
    * **Categorization**: Gemini 1.5 Pro for accurate transaction categorization
    * **Insights**: Gemini 1.5 Flash for fast insights generation
    
    ## Agent System
    * **FileProcessorAgent**: Handles file extraction and data validation
    * **CategorizerAgent**: Categorizes transactions using AI and rules
    * **InsightsAgent**: Generates comprehensive financial insights
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(upload.router, prefix="/api/v1")
app.include_router(categorize.router, prefix="/api/v1")
app.include_router(insights.router, prefix="/api/v1")

@app.get("/", response_model=APIResponse)
async def root():
    """Root endpoint with API information"""
    return APIResponse(
        success=True,
        message="Welcome to Finance Manager Categorizer API",
        data={
            "version": "1.0.0",
            "description": "AI-Powered Bank Statement Analysis and Categorization",
            "endpoints": {
                "health": "/health",
                "docs": "/docs",
                "upload": "/api/v1/upload",
                "categorize": "/api/v1/categorize",
                "insights": "/api/v1/insights"
            },
            "features": [
                "Multi-format file support (CSV, Excel, PDF)",
                "AI-powered transaction categorization",
                "Financial insights generation",
                "Interactive visualizations",
                "Multi-agent processing system"
            ]
        }
    )

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Test Gemini API
        gemini_status = await gemini_service.test_connection()
        
        # Get Agno version
        try:
            import agno
            agno_version = agno.__version__
        except:
            agno_version = "unknown"
        
        # Current timestamp
        from datetime import datetime
        timestamp = datetime.now().isoformat()
        
        return HealthCheckResponse(
            status="healthy",
            gemini_api_status=gemini_status.get('status', 'unknown'),
            agno_version=agno_version,
            timestamp=timestamp
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.get("/api/v1/status", response_model=APIResponse)
async def get_api_status():
    """Get detailed API status including agent team information"""
    try:
        # Get team status
        team_status = await agent_team_service.get_team_status()
        
        # Get Gemini status
        gemini_status = await gemini_service.test_connection()
        
        # System information
        import platform
        import psutil
        
        system_info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": f"{psutil.virtual_memory().total / (1024**3):.2f} GB",
            "memory_available": f"{psutil.virtual_memory().available / (1024**3):.2f} GB"
        }
        
        return APIResponse(
            success=True,
            message="API status retrieved successfully",
            data={
                "api_version": "1.0.0",
                "agent_team": team_status,
                "gemini_api": gemini_status,
                "system_info": system_info,
                "upload_directory": settings.upload_dir,
                "supported_formats": settings.allowed_extensions,
                "max_file_size": settings.max_file_size
            }
        )
        
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "message": f"Endpoint not found: {request.url.path}",
            "error": "Not Found",
            "available_endpoints": [
                "/",
                "/health",
                "/docs",
                "/api/v1/upload",
                "/api/v1/categorize", 
                "/api/v1/insights"
            ]
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler"""
    logger.error(f"Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error occurred",
            "error": "Internal Server Error",
            "request_path": str(request.url.path)
        }
    )

if __name__ == "__main__":
    # Run the application
    logger.info(f"Starting Finance Manager API on {settings.app_host}:{settings.app_port}")
    
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
        access_log=True
    )