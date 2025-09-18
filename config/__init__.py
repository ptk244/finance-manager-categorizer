# config/__init__.py
"""
Configuration module for Finance Manager Categorizer

This module handles all application configuration including:
- Environment variables
- API keys
- Application settings
- File upload configurations
"""

__version__ = "1.0.0"

from .settings import settings

__all__ = ["settings"]