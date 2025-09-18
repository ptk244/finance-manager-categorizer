# agents/__init__.py
"""
AI Agents for Finance Manager using Agno framework

This module contains specialized agents for different aspects of financial analysis:
- FileProcessorAgent: File processing and data extraction
- CategorizerAgent: AI-powered transaction categorization
- InsightsAgent: Financial insights and recommendations generation

Each agent is built using the Agno framework with custom tools and instructions.
"""

__version__ = "1.0.0"

from .file_processor_agent import file_processor_agent
from .categorizer_agent import categorizer_agent  
from .insights_agent import insights_agent

__all__ = [
    "file_processor_agent",
    "categorizer_agent",
    "insights_agent"
]
