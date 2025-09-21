"""
Fixed Categorization Agent that properly handles data transformation
"""
import os
import structlog
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from app.agents.base_agent import BaseFinanceAgent
from app.models.transaction import Transaction, CategorizedTransaction
from app.config import get_settings

logger = structlog.get_logger(__name__)


class CategorizationAgent(BaseFinanceAgent):
    """
    Enhanced categorization agent that properly transforms data for Pydantic models
    """
    
    def __init__(self):
        settings = get_settings()
        super().__init__(
            name="CategorizationAgent",
            model_name=settings.categorization_model,
            role="Expert Financial Transaction Categorization Specialist",
            instructions="""You are an expert financial transaction categorization specialist.
            Analyze each transaction and provide accurate category, subcategory, confidence score, and reasoning.
            
            Standard categories to use:
            - Salary/Income (for salary, bonuses, interest)
            - Groceries (for food shopping)
            - Food & Dining (for restaurants, food delivery)
            - Bills & Utilities (for electricity, water, internet, phone)
            - Transportation (for fuel, taxi, public transport)
            - Entertainment (for movies, games, subscriptions)
            - Shopping (for general purchases, online shopping)
            - Healthcare (for medical expenses, pharmacy)
            - Travel (for trips, hotels, flights)
            - Other (for miscellaneous expenses)
            
            Always respond with valid JSON in the exact format requested."""
        )
    
    async def categorize_transactions(self, transactions: List[Transaction]) -> List[CategorizedTransaction]:
        """
        Categorize a list of transactions
        
        Args:
            transactions: List of Transaction objects to categorize
            
        Returns:
            List of CategorizedTransaction objects
        """
        try:
            self.logger.info("Starting transaction categorization", 
                           transaction_count=len(transactions))
            
            if not transactions:
                return []
            
            # Prepare transaction data for the AI agent
            transaction_data = []
            for i, txn in enumerate(transactions):
                transaction_data.append({
                    "index": i,
                    "date": str(txn.transaction_date),
                    "description": txn.description,
                    "amount": txn.amount,
                    "type": txn.type,
                    "balance": txn.balance
                })
            
            # Create prompt for categorization
            prompt = f"""
            Please categorize the following {len(transactions)} financial transactions.
            
            Return your response in this EXACT JSON format:
            {{
                "transactions": [
                    {{
                        "index": 0,
                        "category": "Category Name",
                        "subcategory": "Subcategory Name",
                        "confidence": 0.95,
                        "reasoning": "Brief explanation"
                    }}
                ]
            }}
            
            Transactions to categorize:
            {transaction_data}
            
            Important: Return only the JSON response, no additional text or formatting.
            """
            
            # Get categorization from AI
            response = self.run(prompt)
            categorization_result = self.parse_json_response(response.content)
            
            self.logger.debug("Raw categorization result", result=categorization_result)
            
            # Transform to CategorizedTransaction objects
            categorized_transactions = []
            
            if not isinstance(categorization_result, dict) or 'transactions' not in categorization_result:
                self.logger.error("Invalid categorization response format")
                return self._create_fallback_categorizations(transactions)
            
            ai_categorizations = categorization_result['transactions']


            
            for i, original_txn in enumerate(transactions):
                try:
                    # Find corresponding AI categorization
                    ai_cat = None
                    for cat in ai_categorizations:
                        if cat.get('index') == i:
                            ai_cat = cat
                            break
                    
                    if not ai_cat:
                        self.logger.warning(f"No categorization found for transaction {i}")
                        ai_cat = {
                            'category': 'Other',
                            'subcategory': 'General',
                            'confidence': 0.5,
                            'reasoning': 'No AI categorization found'
                        }
                    
                    # Create CategorizedTransaction with proper field mapping
                    categorized_txn = CategorizedTransaction(
                        # Base transaction fields
                        transaction_date=original_txn.transaction_date,
                        description=original_txn.description,
                        amount=original_txn.amount,
                        type=original_txn.type,
                        balance=original_txn.balance,
                        reference=original_txn.reference,
                        
                        # Categorization fields
                        category=ai_cat.get('category', 'Other'),
                        subcategory=ai_cat.get('subcategory', 'General'),
                        confidence=float(ai_cat.get('confidence', 0.5)),
                        reasoning=ai_cat.get('reasoning', 'AI categorization'),
                        
                        # Additional computed fields (handled by CategorizedTransaction.__init__)
                        amount_inr=abs(original_txn.amount)
                    )
                    
                    categorized_transactions.append(categorized_txn)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process transaction {i}", error=str(e))
                    # Create fallback categorization for this transaction
                    fallback_txn = self._create_fallback_transaction(original_txn, i)
                    if fallback_txn:
                        categorized_transactions.append(fallback_txn)
            
            self.logger.info("Transaction categorization completed", 
                           successful_count=len(categorized_transactions))
            
            return categorized_transactions
            
        except Exception as e:
            self.logger.error("Categorization process failed", error=str(e))
            return self._create_fallback_categorizations(transactions)
    
    def _create_fallback_categorizations(self, transactions: List[Transaction]) -> List[CategorizedTransaction]:
        """
        Create fallback categorizations when AI processing fails
        """
        self.logger.info("Creating fallback categorizations")
        
        fallback_transactions = []
        
        for i, txn in enumerate(transactions):
            try:
                # Simple rule-based categorization
                category, subcategory = self._simple_categorize(txn.description)
                
                fallback_txn = CategorizedTransaction(
                    # Base transaction fields
                    transaction_date=txn.transaction_date,
                    description=txn.description,
                    amount=txn.amount,
                    type=txn.type,
                    balance=txn.balance,
                    reference=txn.reference,
                    
                    # Categorization fields
                    category=category,
                    subcategory=subcategory,
                    confidence=0.3,  # Low confidence for fallback
                    reasoning="Fallback categorization due to AI processing failure",
                    
                    # Additional computed fields
                    amount_inr=abs(txn.amount)
                )
                
                fallback_transactions.append(fallback_txn)
                
            except Exception as e:
                self.logger.warning(f"Failed to create fallback for transaction {i}", error=str(e))
                continue
        
        return fallback_transactions
    
    def _create_fallback_transaction(self, original_txn: Transaction, index: int) -> Optional[CategorizedTransaction]:
        """
        Create a single fallback transaction
        """
        try:
            category, subcategory = self._simple_categorize(original_txn.description)
            
            return CategorizedTransaction(
                # Base transaction fields
                transaction_date=original_txn.transaction_date,
                description=original_txn.description,
                amount=original_txn.amount,
                type=original_txn.type,
                balance=original_txn.balance,
                reference=original_txn.reference,
                
                # Categorization fields
                category=category,
                subcategory=subcategory,
                confidence=0.4,
                reasoning=f"Fallback categorization for transaction {index}",
                
                # Additional computed fields
                amount_inr=abs(original_txn.amount)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create fallback transaction", error=str(e))
            return None
    
    def _simple_categorize(self, description: str) -> tuple[str, str]:
        """
        Simple rule-based categorization fallback
        """
        desc_lower = description.lower()
        
        # Simple keyword matching
        if any(word in desc_lower for word in ['salary', 'pay', 'income', 'credit']):
            return "Salary/Income", "Salary"
        elif any(word in desc_lower for word in ['grocery', 'supermarket', 'market', 'bazaar']):
            return "Groceries", "Supermarket"
        elif any(word in desc_lower for word in ['restaurant', 'food', 'dining', 'zomato', 'swiggy']):
            return "Food & Dining", "Restaurant"
        elif any(word in desc_lower for word in ['electricity', 'water', 'gas', 'internet', 'phone', 'bill']):
            return "Bills & Utilities", "Utility"
        elif any(word in desc_lower for word in ['fuel', 'petrol', 'taxi', 'uber', 'ola', 'bus', 'train']):
            return "Transportation", "Transport"
        elif any(word in desc_lower for word in ['movie', 'entertainment', 'game', 'netflix']):
            return "Entertainment", "Entertainment"
        elif any(word in desc_lower for word in ['amazon', 'flipkart', 'shopping', 'purchase']):
            return "Shopping", "Online"
        elif any(word in desc_lower for word in ['hospital', 'medical', 'pharmacy', 'medicine', 'doctor']):
            return "Healthcare", "Medical"
        elif any(word in desc_lower for word in ['travel', 'trip', 'hotel', 'flight']):
            return "Travel", "Trip"
        else:
            return "Other", "General"
    
    async def learn_from_correction(self, 
                                  transaction: CategorizedTransaction,
                                  correct_category: str,
                                  correct_subcategory: Optional[str] = None) -> Dict[str, Any]:
        """
        Learn from user corrections (placeholder for future ML implementation)
        """
        try:
            self.logger.info("Processing user correction", 
                           original_category=transaction.category,
                           correct_category=correct_category,
                           description=transaction.description)
            
            # For now, just log the correction
            # In a real implementation, this would update a learning model
            correction_data = {
                "description": transaction.description,
                "amount": transaction.amount,
                "original_category": transaction.category,
                "original_subcategory": transaction.subcategory,
                "correct_category": correct_category,
                "correct_subcategory": correct_subcategory,
                "timestamp": datetime.now().isoformat()
            }
            
            self.logger.info("User correction logged", correction=correction_data)
            
            return {
                "success": True,
                "message": "Correction logged for future learning",
                "correction_data": correction_data
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to process correction: {str(e)}"
            }
    
    def get_categorization_stats(self) -> Dict[str, Any]:
        """
        Get categorization statistics
        """
        return {
            "agent_name": self.name,
            "model": "gemini-2.5-flash",
            "capabilities": [
                "Transaction categorization",
                "Confidence scoring",
                "Fallback categorization",
                "User correction learning"
            ],
            "supported_categories": [
                "Salary/Income", "Groceries", "Food & Dining",
                "Bills & Utilities", "Transportation", "Entertainment",
                "Shopping", "Healthcare", "Travel", "Other"
            ]
        }