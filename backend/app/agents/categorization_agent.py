"""
Fixed Categorization Agent that properly handles data transformation with chunked processing
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
    Enhanced categorization agent with chunked processing and better error handling
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
        self.chunk_size = 10  # Process transactions in smaller chunks
    
    async def categorize_transactions(self, transactions: List[Transaction]) -> List[CategorizedTransaction]:
        """
        Categorize a list of transactions with chunked processing
        
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
            
            # Process transactions in chunks to avoid token limits
            categorized_transactions = []
            
            for i in range(0, len(transactions), self.chunk_size):
                chunk = transactions[i:i + self.chunk_size]
                chunk_result = await self._categorize_chunk(chunk, i)
                categorized_transactions.extend(chunk_result)
                
                self.logger.debug(f"Processed chunk {i//self.chunk_size + 1}", 
                                chunk_size=len(chunk),
                                total_processed=len(categorized_transactions))
            
            self.logger.info("Transaction categorization completed", 
                           successful_count=len(categorized_transactions))
            
            return categorized_transactions
            
        except Exception as e:
            self.logger.error("Categorization process failed", error=str(e))
            return self._create_fallback_categorizations(transactions)
    
    async def _categorize_chunk(self, transactions: List[Transaction], start_index: int = 0) -> List[CategorizedTransaction]:
        """
        Categorize a chunk of transactions
        """
        try:
            # Prepare transaction data for the AI agent
            transaction_data = []
            for i, txn in enumerate(transactions):
                transaction_data.append({
                    "index": start_index + i,
                    "date": str(txn.transaction_date),
                    "description": txn.description[:100],  # Truncate long descriptions
                    "amount": txn.amount,
                    "type": txn.type
                })
            
            # Create simplified prompt
            prompt = f"""Categorize these {len(transactions)} transactions. Return JSON only:
            
            {{"transactions": [
                {{"index": 0, "category": "Category", "subcategory": "Sub", "confidence": 0.9, "reasoning": "Brief reason"}}
            ]}}
            
            Transactions: {transaction_data}"""
            
            # Get categorization with timeout and error handling
            try:
                response = self.run(prompt)
                
                if not response or not response.content:
                    self.logger.warning("Empty response from AI model")
                    return self._create_fallback_chunk(transactions, start_index)
                
                categorization_result = self.parse_json_response(response.content)
                
            except Exception as e:
                self.logger.warning(f"AI request failed: {str(e)}")
                return self._create_fallback_chunk(transactions, start_index)
            
            # Validate response structure
            if not isinstance(categorization_result, dict) or 'transactions' not in categorization_result:
                self.logger.warning("Invalid response structure from AI")
                return self._create_fallback_chunk(transactions, start_index)
            
            ai_categorizations = categorization_result['transactions']
            
            # Transform to CategorizedTransaction objects
            categorized_transactions = []
            
            for i, original_txn in enumerate(transactions):
                try:
                    # Find corresponding AI categorization
                    ai_cat = None
                    target_index = start_index + i
                    
                    for cat in ai_categorizations:
                        if cat.get('index') == target_index:
                            ai_cat = cat
                            break
                    
                    if not ai_cat:
                        self.logger.debug(f"No AI categorization for transaction {target_index}")
                        ai_cat = self._get_rule_based_categorization(original_txn.description)
                    
                    # Create CategorizedTransaction
                    categorized_txn = self._create_categorized_transaction(original_txn, ai_cat)
                    if categorized_txn:
                        categorized_transactions.append(categorized_txn)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process transaction {start_index + i}", error=str(e))
                    # Create fallback for this transaction
                    fallback_txn = self._create_fallback_transaction(original_txn, start_index + i)
                    if fallback_txn:
                        categorized_transactions.append(fallback_txn)
            
            return categorized_transactions
            
        except Exception as e:
            self.logger.error("Chunk processing failed", error=str(e))
            return self._create_fallback_chunk(transactions, start_index)
    
    def _create_categorized_transaction(self, original_txn: Transaction, ai_cat: Dict[str, Any]) -> Optional[CategorizedTransaction]:
        """
        Create a CategorizedTransaction from original transaction and AI categorization
        """
        try:
            return CategorizedTransaction(
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
                
                # Additional computed fields
                amount_inr=abs(original_txn.amount) if original_txn.amount else 0.0
            )
        except Exception as e:
            self.logger.error("Failed to create categorized transaction", error=str(e))
            return None
    
    def _create_fallback_chunk(self, transactions: List[Transaction], start_index: int) -> List[CategorizedTransaction]:
        """
        Create fallback categorizations for a chunk
        """
        fallback_transactions = []
        
        for i, txn in enumerate(transactions):
            fallback_txn = self._create_fallback_transaction(txn, start_index + i)
            if fallback_txn:
                fallback_transactions.append(fallback_txn)
        
        return fallback_transactions
    
    def _create_fallback_categorizations(self, transactions: List[Transaction]) -> List[CategorizedTransaction]:
        """
        Create fallback categorizations when AI processing fails completely
        """
        self.logger.info("Creating fallback categorizations")
        
        fallback_transactions = []
        
        for i, txn in enumerate(transactions):
            try:
                fallback_txn = self._create_fallback_transaction(txn, i)
                if fallback_txn:
                    fallback_transactions.append(fallback_txn)
                    
            except Exception as e:
                self.logger.warning(f"Failed to create fallback for transaction {i}", error=str(e))
                continue
        
        return fallback_transactions
    
    def _create_fallback_transaction(self, original_txn: Transaction, index: int) -> Optional[CategorizedTransaction]:
        """
        Create a single fallback transaction using rule-based categorization
        """
        try:
            rule_cat = self._get_rule_based_categorization(original_txn.description)
            
            return CategorizedTransaction(
                # Base transaction fields
                transaction_date=original_txn.transaction_date,
                description=original_txn.description,
                amount=original_txn.amount,
                type=original_txn.type,
                balance=original_txn.balance,
                reference=original_txn.reference,
                
                # Categorization fields
                category=rule_cat['category'],
                subcategory=rule_cat['subcategory'],
                confidence=rule_cat['confidence'],
                reasoning=rule_cat['reasoning'],
                
                # Additional computed fields
                amount_inr=abs(original_txn.amount) if original_txn.amount else 0.0
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create fallback transaction", error=str(e))
            return None
    
    def _get_rule_based_categorization(self, description: str) -> Dict[str, Any]:
        """
        Get rule-based categorization for a transaction description
        """
        desc_lower = description.lower()
        
        # Enhanced rule-based categorization
        if any(word in desc_lower for word in ['salary', 'pay', 'income', 'credit', 'cms', 'deposit']):
            return {
                'category': 'Salary/Income',
                'subcategory': 'Salary',
                'confidence': 0.7,
                'reasoning': 'Rule-based: Income keywords detected'
            }
        elif any(word in desc_lower for word in ['grocery', 'supermarket', 'market', 'bazaar', 'kirana']):
            return {
                'category': 'Groceries',
                'subcategory': 'Supermarket',
                'confidence': 0.6,
                'reasoning': 'Rule-based: Grocery keywords detected'
            }
        elif any(word in desc_lower for word in ['restaurant', 'food', 'dining', 'zomato', 'swiggy', 'hotel']):
            return {
                'category': 'Food & Dining',
                'subcategory': 'Restaurant',
                'confidence': 0.6,
                'reasoning': 'Rule-based: Food/dining keywords detected'
            }
        elif any(word in desc_lower for word in ['electricity', 'water', 'gas', 'internet', 'phone', 'bill', 'utility']):
            return {
                'category': 'Bills & Utilities',
                'subcategory': 'Utility',
                'confidence': 0.6,
                'reasoning': 'Rule-based: Utility keywords detected'
            }
        elif any(word in desc_lower for word in ['fuel', 'petrol', 'taxi', 'uber', 'ola', 'bus', 'train', 'transport']):
            return {
                'category': 'Transportation',
                'subcategory': 'Transport',
                'confidence': 0.6,
                'reasoning': 'Rule-based: Transportation keywords detected'
            }
        elif any(word in desc_lower for word in ['movie', 'entertainment', 'game', 'netflix', 'amazon prime']):
            return {
                'category': 'Entertainment',
                'subcategory': 'Entertainment',
                'confidence': 0.6,
                'reasoning': 'Rule-based: Entertainment keywords detected'
            }
        elif any(word in desc_lower for word in ['amazon', 'flipkart', 'shopping', 'purchase', 'shop']):
            return {
                'category': 'Shopping',
                'subcategory': 'Online',
                'confidence': 0.6,
                'reasoning': 'Rule-based: Shopping keywords detected'
            }
        elif any(word in desc_lower for word in ['hospital', 'medical', 'pharmacy', 'medicine', 'doctor', 'clinic']):
            return {
                'category': 'Healthcare',
                'subcategory': 'Medical',
                'confidence': 0.6,
                'reasoning': 'Rule-based: Healthcare keywords detected'
            }
        elif any(word in desc_lower for word in ['travel', 'trip', 'hotel', 'flight', 'booking']):
            return {
                'category': 'Travel',
                'subcategory': 'Trip',
                'confidence': 0.6,
                'reasoning': 'Rule-based: Travel keywords detected'
            }
        elif any(word in desc_lower for word in ['atm', 'withdrawal', 'cash']):
            return {
                'category': 'Other',
                'subcategory': 'ATM Withdrawal',
                'confidence': 0.7,
                'reasoning': 'Rule-based: ATM/cash withdrawal detected'
            }
        elif any(word in desc_lower for word in ['transfer', 'neft', 'imps', 'rtgs', 'upi']):
            return {
                'category': 'Other',
                'subcategory': 'Transfer',
                'confidence': 0.7,
                'reasoning': 'Rule-based: Money transfer detected'
            }
        else:
            return {
                'category': 'Other',
                'subcategory': 'General',
                'confidence': 0.4,
                'reasoning': 'Rule-based: Default categorization'
            }
    
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Enhanced JSON parsing with better error handling
        """
        try:
            if not response or response.strip() == '':
                self.logger.warning("Empty response received")
                return {
                    "error": "Empty response",
                    "raw_response": response
                }
            
            # Clean up response
            cleaned_response = response.strip()
            
            # Remove markdown formatting
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            
            cleaned_response = cleaned_response.strip()
            
            # Try to parse JSON
            import json
            return json.loads(cleaned_response)
            
        except json.JSONDecodeError as e:
            self.logger.error("JSON parsing failed", 
                            error=str(e), 
                            response_preview=response[:200] if response else "None")
            return {
                "error": "Failed to parse JSON response",
                "raw_response": response,
                "parse_error": str(e)
            }
        except Exception as e:
            self.logger.error("Unexpected error in JSON parsing", error=str(e))
            return {
                "error": "Unexpected parsing error",
                "raw_response": response,
                "parse_error": str(e)
            }
    
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
            "chunk_size": self.chunk_size,
            "capabilities": [
                "Transaction categorization",
                "Confidence scoring",
                "Fallback categorization",
                "User correction learning",
                "Chunked processing"
            ],
            "supported_categories": [
                "Salary/Income", "Groceries", "Food & Dining",
                "Bills & Utilities", "Transportation", "Entertainment",
                "Shopping", "Healthcare", "Travel", "Other"
            ]
        }