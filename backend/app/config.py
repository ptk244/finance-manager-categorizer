"""
Configuration settings for the Finance Manager application
"""
import os
from typing import List, Dict
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """Application settings"""

    # API Configuration
    app_name: str = "Finance Manager Categorizer API"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="FASTAPI_DEBUG")
    host: str = Field(default="localhost", env="FASTAPI_HOST")
    port: int = Field(default=8000, env="FASTAPI_PORT")

    # Google Gemini Configuration
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    categorization_model: str = Field(env="CATEGORIZATION_MODEL")
    insights_model: str = Field(env="INSIGHTS_MODEL")

    # File Upload Configuration
    max_file_size_bytes: int = Field(default=10 * 1024 * 1024)  # 10MB
    max_file_size_mb: float = Field(default=10.0, env="MAX_FILE_SIZE_MB")
    allowed_file_types: List[str] = Field(
        default=["csv", "xlsx", "xls", "pdf"],
        env="ALLOWED_FILE_TYPES"
    )

    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    agno_log_level: str = Field(default="INFO", env="AGNO_LOG_LEVEL")

    # Processing Configuration
    batch_size: int = Field(default=100, env="BATCH_SIZE")
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    timeout_seconds: int = Field(default=300, env="TIMEOUT_SECONDS")

    # AI Configuration
    temperature: float = Field(default=0.1, env="AI_TEMPERATURE")
    max_tokens: int = Field(default=8192, env="MAX_TOKENS")

    # Categories Configuration
    default_categories: List[str] = [
        "Food & Dining", "Groceries", "Shopping", "Bills & Utilities",
        "Travel", "Transportation", "Entertainment", "Healthcare",
        "Education", "Investments", "Salary/Income", "Bank Fees",
        "Insurance", "Loans", "Miscellaneous"
    ]

    # Indian Bank Specific Settings
    indian_bank_formats: Dict = {
        "ICICI": {
            "date_formats": ["%d/%m/%Y", "%d-%m-%Y"],
            "amount_columns": ["Debit", "Credit", "Amount"],
            "description_columns": ["Transaction Details", "Narration", "Description"]
        },
        "SBI": {
            "date_formats": ["%d %b %Y", "%d/%m/%Y"],
            "amount_columns": ["Debit", "Credit", "Amount"],
            "description_columns": ["Description", "Narration"]
        },
        "HDFC": {
            "date_formats": ["%d/%m/%y", "%d/%m/%Y"],
            "amount_columns": ["Debit Amount", "Credit Amount", "Amount"],
            "description_columns": ["Narration", "Description"]
        }
    }

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",   # 🔑 allows extra env vars without throwing errors
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Convert string list to actual list if needed
        if isinstance(self.allowed_file_types, str):
            self.allowed_file_types = self.allowed_file_types.split(",")

        # Set max_file_size_bytes from MB
        self.max_file_size_bytes = int(self.max_file_size_mb * 1024 * 1024)


class AgnoSettings(BaseSettings):
    """Agno-specific configuration"""

    # Team Configuration
    team_name: str = Field(default="FinanceTeam", env="AGNO_TEAM_NAME")

    # Agent Configuration
    categorization_agent_name: str = Field(default="CategorizationAgent", env="CATEGORIZATION_AGENT_NAME")
    insights_agent_name: str = Field(default="InsightsAgent", env="INSIGHTS_AGENT_NAME")

    # Memory Configuration
    use_memory: bool = Field(default=True, env="AGNO_USE_MEMORY")
    memory_type: str = Field(default="short_term", env="AGNO_MEMORY_TYPE")

    # Tool Configuration
    enable_tools: bool = Field(default=True, env="AGNO_ENABLE_TOOLS")

    # Workflow Configuration
    max_workflow_steps: int = Field(default=50, env="MAX_WORKFLOW_STEPS")
    workflow_timeout: int = Field(default=600, env="WORKFLOW_TIMEOUT")

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",   # 🔑 allows extra env vars without throwing errors
    }


# Global settings instances
settings = Settings()
agno_settings = AgnoSettings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings


def get_agno_settings() -> AgnoSettings:
    """Get Agno settings"""
    return agno_settings


# Validation
def validate_settings():
    """Validate critical settings"""
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required")

    if not settings.allowed_file_types:
        raise ValueError("At least one file type must be allowed")

    if settings.max_file_size_mb <= 0:
        raise ValueError("MAX_FILE_SIZE_MB must be greater than 0")

    return True


# Initialize validation
validate_settings()
