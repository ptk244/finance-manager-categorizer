import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Gemini API Configuration
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model_categorization: str = os.getenv("GEMINI_MODEL_CATEGORIZATION", "gemini-1.5-pro")
    gemini_model_insights: str = os.getenv("GEMINI_MODEL_INSIGHTS", "gemini-1.5-flash")
    
    # Application Configuration
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # File Upload Configuration
    max_file_size: str = os.getenv("MAX_FILE_SIZE", "50MB")
    allowed_extensions: list = [".csv", ".xlsx", ".xls", ".pdf"]
    
    # Agno Configuration
    agno_log_level: str = os.getenv("AGNO_LOG_LEVEL", "INFO")
    
    # Upload Directory
    upload_dir: str = "uploads"
    
    class Config:
        env_file = ".env"

settings = Settings()