# services/__init__.py
"""
Business logic services for Finance Manager

This module contains core business logic and external service integrations:
- Gemini AI service for transaction categorization and insights
- Agent team service for multi-agent workflow orchestration
- Database services (if implemented)
- External API integrations
"""

__version__ = "1.0.0"

from .gemini_service import gemini_service
from .agent_team_service import agent_team_service

__all__ = [
    "gemini_service",
    "agent_team_service"
]
