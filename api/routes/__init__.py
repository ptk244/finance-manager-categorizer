# api/routes/__init__.py
"""
API route modules for Finance Manager

This module organizes API routes by functionality:
- upload.py: File upload and processing endpoints
- categorize.py: Transaction categorization endpoints  
- insights.py: Financial insights and visualization endpoints

All routes follow RESTful conventions and include proper error handling.
"""

__version__ = "1.0.0"

from . import upload, categorize, insights

__all__ = ["upload", "categorize", "insights"]

