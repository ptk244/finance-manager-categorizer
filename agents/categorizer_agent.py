from typing import Any, Dict, List

from agno.agent import Agent
from loguru import logger

from models.transaction import (ProcessedBankStatement, SpendingCategory,
                                Transaction)
from services.gemini_service import gemini_service
from tools.categorization_tools import categorization_tools


class CategorizerAgent:
    """Agent responsible for categorizing transactions using Gemini Pro model"""
    
    def __init__(self):
        self.agent = Agent(
            name="CategorizerAgent",
            description="Specialized in categorizing financial transactions using AI and rule-based approaches",
            instructions=[
                "You are a financial transaction categorization expert.",
                "Your job is to analyze transaction descriptions and categorize them accurately.",
                "Use both AI-powered analysis and rule-based patterns for best results.",
                "Handle Indian financial context and common transaction patterns.",
                "Provide confidence scores for each categorization.",
                "Apply business rules and validation to improve accuracy.",
                "Focus on practical spending categories that users can understand and act upon.",
                "Handle edge cases and ambiguous transactions gracefully.",
                "Maintain consistency across similar transactions."
            ],
            model=f"gemini/{gemini_service.categorization_model.model_name}",
            tools=[categorization_tools],
            # show_tool_calls=True,
            debug_mode=True
        )
    
    async def categorize_transactions(self, processed_statement: ProcessedBankStatement) -> Dict[str, Any]:
        """Categorize all transactions in the processed bank statement"""
        try:
            logger.info(f"Starting categorization for {len(processed_statement.transactions)} transactions")
            
            # Convert transactions to dict format for processing
            transaction_dicts = []
            for transaction in processed_statement.transactions:
                transaction_dicts.append({
                    'date': transaction.date.isoformat(),
                    'description': transaction.description,
                    'amount': transaction.amount,
                    'transaction_type': transaction.transaction_type.value,
                    'balance': transaction.balance
                })
            
            # Batch categorize transactions
            categorized_dicts = await categorization_tools.batch_categorize_transactions(transaction_dicts)
            
            # Apply validation and refinement
            refined_dicts = categorization_tools.validate_and_refine_categories(categorized_dicts)
            
            # Convert back to Transaction objects with categories
            categorized_transactions = []
            for trans_dict in refined_dicts:
                try:
                    # Map category string to enum
                    category = self._map_category_to_enum(trans_dict.get('category', 'Other'))
                    
                    transaction = Transaction(
                        date=trans_dict['date'],
                        description=trans_dict['description'],
                        amount=trans_dict['amount'],
                        transaction_type=trans_dict['transaction_type'],
                        balance=trans_dict.get('balance'),
                        category=category,
                        confidence_score=trans_dict.get('confidence_score', 0.5)
                    )
                    
                    categorized_transactions.append(transaction)
                    
                except Exception as e:
                    logger.warning(f"Failed to convert transaction: {str(e)}")
                    continue
            
            # Update processed statement with categorized transactions
            updated_statement = ProcessedBankStatement(
                file_name=processed_statement.file_name,
                total_transactions=len(categorized_transactions),
                date_range=processed_statement.date_range,
                total_debits=processed_statement.total_debits,
                total_credits=processed_statement.total_credits,
                current_balance=processed_statement.current_balance,
                transactions=categorized_transactions
            )
            
            # Generate categorization statistics
            categorization_stats = self._generate_categorization_stats(categorized_transactions)
            
            logger.info(f"Successfully categorized {len(categorized_transactions)} transactions")
            
            return {
                'success': True,
                'categorized_statement': updated_statement,
                'categorization_stats': categorization_stats
            }
            
        except Exception as e:
            logger.error(f"Categorization failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'categorized_statement': None
            }
    
    async def recategorize_transaction(self, transaction: Transaction, force_category: str = None) -> Dict[str, Any]:
        """Recategorize a single transaction, optionally forcing a specific category"""
        try:
            if force_category:
                # Manual override
                category = self._map_category_to_enum(force_category)
                updated_transaction = Transaction(
                    date=transaction.date,
                    description=transaction.description,
                    amount=transaction.amount,
                    transaction_type=transaction.transaction_type,
                    balance=transaction.balance,
                    category=category,
                    confidence_score=1.0  # Full confidence for manual override
                )
                
                return {
                    'success': True,
                    'transaction': updated_transaction,
                    'method': 'manual_override'
                }
            else:
                # Re-run AI categorization
                result = await categorization_tools.categorize_single_transaction(
                    transaction.description,
                    transaction.amount,
                    transaction.transaction_type.value
                )
                
                category = self._map_category_to_enum(result.get('category', 'Other'))
                
                updated_transaction = Transaction(
                    date=transaction.date,
                    description=transaction.description,
                    amount=transaction.amount,
                    transaction_type=transaction.transaction_type,
                    balance=transaction.balance,
                    category=category,
                    confidence_score=result.get('confidence', 0.5)
                )
                
                return {
                    'success': True,
                    'transaction': updated_transaction,
                    'method': result.get('method', 'ai_recategorization')
                }
                
        except Exception as e:
            logger.error(f"Recategorization failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'transaction': transaction
            }
    
    def get_category_summary(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Generate comprehensive category-wise summary"""
        try:
            category_stats = {}
            total_amount = 0
            total_transactions = len(transactions)
            
            # Process each transaction
            for transaction in transactions:
                if transaction.transaction_type.value == 'debit':  # Only consider expenses
                    category = transaction.category.value if transaction.category else 'Other'
                    
                    if category not in category_stats:
                        category_stats[category] = {
                            'total_amount': 0,
                            'transaction_count': 0,
                            'transactions': []
                        }
                    
                    category_stats[category]['total_amount'] += transaction.amount
                    category_stats[category]['transaction_count'] += 1
                    category_stats[category]['transactions'].append({
                        'date': transaction.date.strftime('%Y-%m-%d'),
                        'description': transaction.description,
                        'amount': transaction.amount
                    })
                    
                    total_amount += transaction.amount
            
            # Calculate percentages and averages
            category_summary = {}
            for category, stats in category_stats.items():
                category_summary[category] = {
                    'total_amount': round(stats['total_amount'], 2),
                    'transaction_count': stats['transaction_count'],
                    'percentage': round((stats['total_amount'] / total_amount) * 100, 1) if total_amount > 0 else 0,
                    'avg_transaction': round(stats['total_amount'] / stats['transaction_count'], 2),
                    'sample_transactions': stats['transactions'][:3]  # Show top 3 transactions
                }
            
            # Sort by total amount
            sorted_categories = dict(sorted(category_summary.items(), key=lambda x: x[1]['total_amount'], reverse=True))
            
            return {
                'category_breakdown': sorted_categories,
                'total_categorized_amount': total_amount,
                'total_categories': len(sorted_categories),
                'top_category': list(sorted_categories.keys())[0] if sorted_categories else None,
                'category_distribution': {k: v['total_amount'] for k, v in sorted_categories.items()}
            }
            
        except Exception as e:
            logger.error(f"Category summary generation failed: {str(e)}")
            return {
                'error': str(e),
                'category_breakdown': {},
                'total_categorized_amount': 0
            }
    
    def _map_category_to_enum(self, category_string: str) -> SpendingCategory:
        """Map category string to SpendingCategory enum"""
        category_mapping = {
            'Food & Dining': SpendingCategory.FOOD_DINING,
            'Groceries': SpendingCategory.GROCERIES,
            'Transportation': SpendingCategory.TRANSPORTATION,
            'Entertainment': SpendingCategory.ENTERTAINMENT,
            'Utilities': SpendingCategory.UTILITIES,
            'Shopping': SpendingCategory.SHOPPING,
            'Healthcare': SpendingCategory.HEALTHCARE,
            'Education': SpendingCategory.EDUCATION,
            'Travel': SpendingCategory.TRAVEL,
            'Investment': SpendingCategory.INVESTMENT,
            'Salary': SpendingCategory.SALARY,
            'Business': SpendingCategory.BUSINESS,
            'Rent/Mortgage': SpendingCategory.RENT_MORTGAGE,
            'Insurance': SpendingCategory.INSURANCE,
            'Fuel': SpendingCategory.FUEL,
            'ATM/Cash': SpendingCategory.ATM_CASH,
            'Transfer': SpendingCategory.TRANSFER,
            'Fees & Charges': SpendingCategory.FEES_CHARGES,
            'Other': SpendingCategory.OTHER
        }
        
        return category_mapping.get(category_string, SpendingCategory.OTHER)
    
    def _generate_categorization_stats(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Generate detailed categorization statistics"""
        try:
            total_transactions = len(transactions)
            categorized_transactions = [t for t in transactions if t.category and t.category != SpendingCategory.OTHER]
            
            confidence_scores = [t.confidence_score for t in transactions if t.confidence_score is not None]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            high_confidence_count = len([s for s in confidence_scores if s >= 0.8])
            medium_confidence_count = len([s for s in confidence_scores if 0.5 <= s < 0.8])
            low_confidence_count = len([s for s in confidence_scores if s < 0.5])
            
            return {
                'total_transactions': total_transactions,
                'categorized_transactions': len(categorized_transactions),
                'categorization_rate': (len(categorized_transactions) / total_transactions) * 100 if total_transactions > 0 else 0,
                'average_confidence': round(avg_confidence, 2),
                'confidence_distribution': {
                    'high': high_confidence_count,
                    'medium': medium_confidence_count,
                    'low': low_confidence_count
                },
                'unique_categories': len(set([t.category for t in transactions if t.category]))
            }
            
        except Exception as e:
            logger.error(f"Stats generation failed: {str(e)}")
            return {
                'total_transactions': len(transactions),
                'error': str(e)
            }

# Create agent instance
categorizer_agent = CategorizerAgent()