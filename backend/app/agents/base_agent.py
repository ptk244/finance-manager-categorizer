"""
Enhanced base agent class for finance-related AI agents with robust data handling
"""
import json
import structlog
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date
from decimal import Decimal
from agno.agent import Agent
from agno.models.google import Gemini
from app.config import get_settings, get_agno_settings
from agno.memory import MemoryManager, UserMemory
from pydantic import BaseModel, ValidationError

_global_memory_manager = MemoryManager()

logger = structlog.get_logger(__name__)


class BaseFinanceAgent(Agent):
    """
    Enhanced base agent class for all finance-related agents.
    Provides common functionality, standardized setup, and robust data transformation.
    """
    
    def __init__(
        self,
        name: str,
        model_name: str,
        role: str,
        instructions: str,
        tools: Optional[List] = None,
        response_model: Optional[BaseModel] = None,
        **kwargs
    ):
        """
        Initialize the base finance agent
        
        Args:
            name: Agent name
            model_name: Gemini model to use
            role: Agent role description
            instructions: Detailed instructions for the agent
            tools: List of tools to provide to the agent
            response_model: Pydantic model for response validation
            **kwargs: Additional arguments for Agent
        """
        settings = get_settings()
        agno_settings = get_agno_settings()
        
        # Initialize Gemini model
        model = Gemini(
            id=model_name,
            api_key=settings.gemini_api_key,
            temperature=settings.temperature,
            max_output_tokens=settings.max_tokens
        )
        
        # Prepare agent configuration
        agent_config = {
            "name": name,
            "model": model,
            "role": role,
            "instructions": instructions,
            "markdown": True,
            **kwargs
        }
        
        # Add tools if provided
        if tools:
            agent_config["tools"] = tools
        
        # Add memory if enabled
        if agno_settings.use_memory:
            user_memory = UserMemory(name, _global_memory_manager)
            self.memory = user_memory
        
        super().__init__(**agent_config)
        
        self.settings = settings
        self.agno_settings = agno_settings
        self.response_model = response_model
        self.logger = logger.bind(agent=name)
        
        self.logger.info("Agent initialized", 
                        model=model_name, 
                        role=role)
    
    def format_response(self, content: Any) -> Dict[str, Any]:
        """
        Format agent response in a standardized way
        
        Args:
            content: Response content
            
        Returns:
            Formatted response dictionary
        """
        return {
            "agent": self.name,
            "model": self.model.model_name if hasattr(self.model, 'model_name') else "unknown",
            "content": content,
            "timestamp": self._get_timestamp()
        }
    
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON response from agent, handling potential formatting issues
        
        Args:
            response: Raw response string from agent
            
        Returns:
            Parsed JSON dictionary
        """
        try:
            # Try to parse as JSON directly
            if isinstance(response, str):
                # Clean up markdown formatting if present
                cleaned_response = response.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]
                cleaned_response = cleaned_response.strip()
                
                return json.loads(cleaned_response)
            else:
                return response
                
        except json.JSONDecodeError as e:
            self.logger.error("Failed to parse JSON response", error=str(e), response=response[:500])
            # Return a structured error response
            return {
                "error": "Failed to parse response",
                "raw_response": response,
                "parse_error": str(e)
            }
    
    def transform_transaction_data(self, raw_transaction: Dict[str, Any], 
                                 categorization_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Transform raw transaction data to match expected Pydantic model fields
        
        Args:
            raw_transaction: Raw transaction data from file processing
            categorization_result: Optional categorization data from agent
            
        Returns:
            Transformed transaction data
        """
        transformed = {}
        
        # Handle date field mapping
        if 'date' in raw_transaction:
            date_value = raw_transaction['date']
            if isinstance(date_value, str):
                try:
                    # Try parsing different date formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']:
                        try:
                            parsed_date = datetime.strptime(date_value, fmt).date()
                            break
                        except ValueError:
                            continue
                    else:
                        # If no format works, use current date as fallback
                        parsed_date = date.today()
                        self.logger.warning("Could not parse date, using today", 
                                          original_date=date_value)
                    transformed['transaction_date'] = parsed_date
                except Exception as e:
                    self.logger.warning("Date parsing failed", error=str(e))
                    transformed['transaction_date'] = date.today()
            elif isinstance(date_value, (date, datetime)):
                transformed['transaction_date'] = date_value if isinstance(date_value, date) else date_value.date()
            else:
                transformed['transaction_date'] = date.today()
        else:
            transformed['transaction_date'] = date.today()
        
        # Handle amount field mapping
        amount_fields = ['amount', 'amount (inr)', 'amount_inr', 'value']
        amount_value = None
        
        for field in amount_fields:
            if field in raw_transaction and raw_transaction[field] is not None:
                amount_value = raw_transaction[field]
                break
        
        if amount_value is not None:
            try:
                # Clean and convert amount
                if isinstance(amount_value, str):
                    # Remove currency symbols and commas
                    cleaned_amount = amount_value.replace(',', '').replace('₹', '').replace('INR', '').strip()
                    # Handle negative amounts (withdrawals)
                    if cleaned_amount.startswith('(') and cleaned_amount.endswith(')'):
                        cleaned_amount = '-' + cleaned_amount[1:-1]
                    amount_value = float(cleaned_amount)
                
                transformed['amount'] = float(amount_value)
                transformed['amount_inr'] = float(abs(amount_value))  # Store absolute value for amount_inr
                
            except (ValueError, TypeError) as e:
                self.logger.warning("Amount parsing failed", error=str(e), amount=amount_value)
                transformed['amount'] = 0.0
                transformed['amount_inr'] = 0.0
        else:
            transformed['amount'] = 0.0
            transformed['amount_inr'] = 0.0
        
        # Handle description
        description_fields = ['description', 'desc', 'transaction_description', 'details']
        for field in description_fields:
            if field in raw_transaction and raw_transaction[field]:
                transformed['description'] = str(raw_transaction[field])
                break
        else:
            transformed['description'] = "Unknown transaction"
        
        # Handle balance
        balance_fields = ['balance', 'balance (inr)', 'closing_balance']
        for field in balance_fields:
            if field in raw_transaction and raw_transaction[field] is not None:
                try:
                    balance_value = raw_transaction[field]
                    if isinstance(balance_value, str):
                        balance_value = balance_value.replace(',', '').replace('₹', '').replace('INR', '').strip()
                    transformed['balance'] = float(balance_value)
                    break
                except (ValueError, TypeError):
                    continue
        
        # Add categorization data if provided
        if categorization_result:
            transformed.update({
                'category': categorization_result.get('category', 'Other'),
                'subcategory': categorization_result.get('subcategory', 'General'),
                'confidence': categorization_result.get('confidence', 0.0),
                'reasoning': categorization_result.get('reasoning', 'No reasoning provided')
            })
        
        # Add metadata
        transformed['metadata'] = {
            'processed_at': self._get_timestamp(),
            'agent': self.name,
            'original_data_keys': list(raw_transaction.keys())
        }
        
        return transformed
    
    def validate_and_transform_response(self, response_data: Any, 
                                      raw_transactions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Validate and transform agent response using Pydantic model
        
        Args:
            response_data: Raw response data from agent
            raw_transactions: Optional raw transaction data for transformation
            
        Returns:
            Validated and transformed response
        """
        try:
            # Parse JSON if needed
            if isinstance(response_data, str):
                response_data = self.parse_json_response(response_data)
            
            # Check for errors in parsed data
            if isinstance(response_data, dict) and 'error' in response_data:
                return response_data
            
            # Transform transaction data if this is a categorization response
            if (raw_transactions and isinstance(response_data, dict) 
                and 'transactions' in response_data):
                
                transformed_transactions = []
                categorization_results = response_data['transactions']
                
                for i, raw_transaction in enumerate(raw_transactions):
                    # Find corresponding categorization result
                    cat_result = None
                    for cat in categorization_results:
                        if cat.get('index', -1) == i:
                            cat_result = cat
                            break
                    
                    # Transform the transaction
                    transformed_transaction = self.transform_transaction_data(
                        raw_transaction, cat_result
                    )
                    transformed_transactions.append(transformed_transaction)
                
                response_data['transactions'] = transformed_transactions
            
            # Validate using Pydantic model if available
            if self.response_model:
                try:
                    validated_data = self.response_model.model_validate(response_data)
                    return validated_data.model_dump()
                except ValidationError as e:
                    self.logger.error("Validation failed", error=str(e), data=response_data)
                    # Return structured validation error
                    return {
                        "error": "Validation failed",
                        "validation_errors": e.errors(),
                        "raw_data": response_data
                    }
            
            return response_data
            
        except Exception as e:
            return self.handle_error(e, "Response validation and transformation")
    
    def create_fallback_response(self, error_context: str = "") -> Dict[str, Any]:
        """
        Create a fallback response when processing fails
        
        Args:
            error_context: Context about the error
            
        Returns:
            Fallback response
        """
        timestamp = self._get_timestamp()
        
        if "categorization" in error_context.lower():
            return {
                "transactions": [],
                "summary": {
                    "total_transactions": 0,
                    "processed_successfully": 0,
                    "failed_processing": 0
                },
                "metadata": {
                    "processed_at": timestamp,
                    "agent": self.name,
                    "error": error_context,
                    "fallback_used": True
                }
            }
        elif "insights" in error_context.lower():
            return {
                "insights": {
                    "key_insights": [],
                    "spending_behavior": {
                        "total_spending": 0.0,
                        "average_transaction": 0.0,
                        "spending_trend": "insufficient_data"
                    },
                    "recommendations": [],
                    "financial_health": {
                        "score": 0,
                        "status": "insufficient_data"
                    },
                    "statistical_insights": {},
                    "metadata": {
                        "processed_at": timestamp,
                        "agent": self.name,
                        "error": error_context,
                        "fallback_used": True
                    }
                }
            }
        else:
            return {
                "error": True,
                "message": f"Processing failed: {error_context}",
                "timestamp": timestamp,
                "agent": self.name,
                "fallback_used": True
            }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.now().isoformat()
    
    def validate_input(self, data: Any) -> bool:
        """
        Validate input data before processing
        
        Args:
            data: Input data to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not data:
            self.logger.warning("Empty input data provided")
            return False
        
        return True
    
    def handle_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        Handle and log errors in a standardized way
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            Standardized error response
        """
        error_msg = f"Agent error in {self.name}: {str(error)}"
        if context:
            error_msg += f" (Context: {context})"
        
        self.logger.error(error_msg, error_type=type(error).__name__)
        
        return {
            "error": True,
            "message": error_msg,
            "agent": self.name,
            "error_type": type(error).__name__,
            "timestamp": self._get_timestamp()
        }
    
    async def process_with_retry(self, 
                               process_func,
                               max_retries: Optional[int] = None,
                               *args, **kwargs) -> Dict[str, Any]:
        """
        Process with retry logic
        
        Args:
            process_func: Function to execute with retry
            max_retries: Maximum number of retries (uses settings default if None)
            *args, **kwargs: Arguments to pass to process_func
            
        Returns:
            Processing result
        """
        if max_retries is None:
            max_retries = self.settings.max_retries
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                self.logger.debug("Processing attempt", attempt=attempt + 1)
                result = await process_func(*args, **kwargs)
                
                if attempt > 0:
                    self.logger.info("Processing succeeded after retry", 
                                   attempt=attempt + 1)
                
                return result
                
            except Exception as e:
                last_error = e
                self.logger.warning("Processing attempt failed", 
                                  attempt=attempt + 1, 
                                  error=str(e))
                
                if attempt == max_retries:
                    break
        
        # All retries exhausted
        return self.handle_error(last_error, f"Failed after {max_retries + 1} attempts")
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """
        Get agent statistics and metadata
        
        Returns:
            Agent statistics dictionary
        """
        return {
            "name": self.name,
            "role": self.role if hasattr(self, 'role') else "Unknown",
            "model": self.model.model_name if hasattr(self.model, 'model_name') else "Unknown",
            "tools_count": len(self.tools) if hasattr(self, 'tools') and self.tools else 0,
            "memory_enabled": self.agno_settings.use_memory,
            "has_response_model": self.response_model is not None,
            "created_at": self._get_timestamp()
        }