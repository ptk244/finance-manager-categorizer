import google.generativeai as genai
from config.settings import settings
from typing import Dict, Any, List
import json
from loguru import logger

import re

def extract_json(text: str) -> dict:
    """Extract and parse JSON object from Gemini response text."""
    try:
        # Try direct JSON load
        return json.loads(text)
    except Exception:
        # Fallback: extract JSON substring
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return {}


class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.categorization_model = genai.GenerativeModel(settings.gemini_model_categorization)
        self.insights_model = genai.GenerativeModel(settings.gemini_model_insights)
        
    async def test_connection(self) -> Dict[str, Any]:
        """Test if Gemini API is working properly"""
        try:
            response = await self.categorization_model.generate_content_async("Hello, are you working?")
            return {
                "status": "connected",
                "model_categorization": settings.gemini_model_categorization,
                "model_insights": settings.gemini_model_insights,
                "response": response.text[:50] + "..." if len(response.text) > 50 else response.text
            }
        except Exception as e:
            logger.error(f"Gemini API connection failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def categorize_transaction(self, description: str, amount: float, transaction_type: str) -> Dict[str, Any]:
        """Categorize a single transaction using Gemini Pro"""
        prompt = f"""
        You are a financial transaction categorizer. Analyze the following transaction and categorize it.
        
        Transaction Details:
        - Description: {description}
        - Amount: ₹{amount}
        - Type: {transaction_type}
        
        Available Categories:
        - Food & Dining
        - Groceries
        - Transportation
        - Entertainment
        - Utilities
        - Shopping
        - Healthcare
        - Education
        - Travel
        - Investment
        - Salary
        - Business
        - Rent/Mortgage
        - Insurance
        - Fuel
        - ATM/Cash
        - Transfer
        - Fees & Charges
        - Other
        
        Return ONLY a JSON object with:
        {{
            "category": "category_name",
            "confidence": 0.95,
            "reasoning": "brief explanation"
        }}
        """
        
        try:
            response = await self.categorization_model.generate_content_async(prompt)
            result = extract_json(response.text.strip())
            return result
        except Exception as e:
            logger.error(f"Categorization failed: {str(e)}")
            return {
                "category": "Other",
                "confidence": 0.1,
                "reasoning": f"Error in categorization: {str(e)}"
            }
    
    async def generate_insights(self, transactions_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate financial insights using Gemini Flash"""
        prompt = f"""
        You are a personal finance advisor. Analyze the following transaction data and provide insights.
        
        Transaction Summary:
        - Total Transactions: {transactions_data.get('total_transactions', 0)}
        - Total Expenses: ₹{transactions_data.get('total_debits', 0)}
        - Total Income: ₹{transactions_data.get('total_credits', 0)}
        - Net Savings: ₹{transactions_data.get('total_credits', 0) - transactions_data.get('total_debits', 0)}
        
        Category Breakdown:
        {json.dumps(transactions_data.get('category_breakdown', {}), indent=2)}
        
        Top Transactions:
        {json.dumps(transactions_data.get('top_transactions', []), indent=2)}
        
        Generate insights in the following format:
        {{
            "summary": "Overall financial summary in 2-3 sentences",
            "key_insights": [
                "Insight 1 (e.g., 'X% of expenses went to Food & Dining')",
                "Insight 2 (e.g., 'Largest expense was ₹X at Y')",
                "Insight 3"
            ],
            "recommendations": [
                "Actionable recommendation 1",
                "Actionable recommendation 2",
                "Actionable recommendation 3"
            ],
            "spending_patterns": "Analysis of spending patterns",
            "savings_potential": "Areas where user can save money"
        }}
        
        Make insights specific to Indian financial context and use ₹ for amounts.
        """
        
        try:
            response = await self.insights_model.generate_content_async(prompt)
            result = extract_json(response.text.strip())
            return result
        except Exception as e:
            logger.error(f"Insights generation failed: {str(e)}")
            return {
                "summary": "Unable to generate detailed insights due to processing error.",
                "key_insights": ["Analysis temporarily unavailable"],
                "recommendations": ["Please try again later"],
                "spending_patterns": "Unable to analyze patterns",
                "savings_potential": "Unable to identify savings opportunities"
            }

# Singleton instance
gemini_service = GeminiService()