from agno import Tool
from typing import List, Dict, Any, Optional
import re
from loguru import logger
from services.gemini_service import gemini_service

class CategorizationTools:
    """Custom tools for transaction categorization with rule-based fallback"""
    
    def __init__(self):
        # Rule-based categorization patterns
        self.category_patterns = {
            'Food & Dining': [
                r'swiggy|zomato|uber eats|food|restaurant|cafe|pizza|burger|mcdonald|kfc|subway|domino',
                r'dining|lunch|dinner|breakfast|meal|eatery|bistro|diner'
            ],
            'Groceries': [
                r'grocery|supermarket|big bazaar|dmart|reliance|fresh|vegetable|fruit|market',
                r'walmart|kroger|safeway|whole foods|trader joe|costco|sam club'
            ],
            'Transportation': [
                r'uber|ola|taxi|cab|bus|train|metro|railway|transport|travel|petrol|diesel',
                r'parking|toll|fuel|gas|station|automobile'
            ],
            'Entertainment': [
                r'movie|cinema|theatre|netflix|amazon prime|hotstar|spotify|youtube|game',
                r'entertainment|show|concert|music|video|streaming'
            ],
            'Utilities': [
                r'electricity|water|gas|internet|broadband|wifi|phone|mobile|recharge',
                r'bill|utility|service|connection|jio|airtel|vodafone|bsnl'
            ],
            'Shopping': [
                r'amazon|flipkart|myntra|ajio|shopping|mall|store|retail|purchase',
                r'cloth|dress|shoe|fashion|electronic|gadget|appliance'
            ],
            'Healthcare': [
                r'hospital|clinic|doctor|medical|pharmacy|medicine|health|dental',
                r'appointment|treatment|checkup|consultation|drug|tablet'
            ],
            'Education': [
                r'school|college|university|course|class|tuition|education|learning',
                r'book|study|exam|fee|admission|library'
            ],
            'Travel': [
                r'hotel|flight|airline|booking|trip|vacation|holiday|tourism|resort',
                r'makemytrip|goibibo|cleartrip|yatra|expedia|airbnb|oyo'
            ],
            'Investment': [
                r'mutual fund|sip|investment|stock|share|trading|demat|broker',
                r'zerodha|groww|upstox|angel|5paisa|equity|bond|fd|rd'
            ],
            'Salary': [
                r'salary|wage|income|pay|payroll|employer|company|organization'
            ],
            'Business': [
                r'business|office|supplies|equipment|software|license|subscription',
                r'professional|service|consultant|freelance|contract'
            ],
            'Rent/Mortgage': [
                r'rent|lease|mortgage|housing|apartment|flat|house|property',
                r'landlord|tenant|real estate|home loan|emi'
            ],
            'Insurance': [
                r'insurance|policy|premium|life|health|vehicle|car|bike|motor',
                r'lic|hdfc|icici|sbi|bajaj|max|star health'
            ],
            'Fuel': [
                r'petrol|diesel|fuel|gas|station|hp|bharat|indian oil|shell'
            ],
            'ATM/Cash': [
                r'atm|cash|withdrawal|deposit|branch|bank counter'
            ],
            'Transfer': [
                r'transfer|upi|neft|rtgs|imps|paytm|gpay|phonepe|whatsapp pay',
                r'send|receive|payment|wallet'
            ],
            'Fees & Charges': [
                r'fee|charge|penalty|fine|tax|gst|service charge|processing',
                r'annual|maintenance|transaction|overdraft'
            ]
        }
    
    @Tool
    async def categorize_single_transaction(self, description: str, amount: float, transaction_type: str) -> Dict[str, Any]:
        """Categorize a single transaction using AI with rule-based fallback"""
        try:
            # First try rule-based categorization
            rule_based_result = self._rule_based_categorization(description)
            
            if rule_based_result['confidence'] > 0.7:
                return rule_based_result
            
            # If rule-based confidence is low, use AI
            ai_result = await gemini_service.categorize_transaction(description, amount, transaction_type)
            
            # Combine results for better accuracy
            if ai_result.get('confidence', 0) > rule_based_result['confidence']:
                return {
                    'category': ai_result.get('category', 'Other'),
                    'confidence': ai_result.get('confidence', 0.5),
                    'reasoning': ai_result.get('reasoning', 'AI-based categorization'),
                    'method': 'ai'
                }
            else:
                return {
                    **rule_based_result,
                    'method': 'rule_based'
                }
                
        except Exception as e:
            logger.error(f"Categorization failed: {str(e)}")
            return {
                'category': 'Other',
                'confidence': 0.1,
                'reasoning': f'Error in categorization: {str(e)}',
                'method': 'error'
            }
    
    @Tool
    async def batch_categorize_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Categorize multiple transactions efficiently"""
        categorized_transactions = []
        
        for transaction in transactions:
            try:
                result = await self.categorize_single_transaction(
                    transaction['description'],
                    transaction['amount'],
                    transaction['transaction_type']
                )
                
                transaction['category'] = result['category']
                transaction['confidence_score'] = result['confidence']
                transaction['categorization_method'] = result.get('method', 'unknown')
                
                categorized_transactions.append(transaction)
                
            except Exception as e:
                logger.warning(f"Failed to categorize transaction: {str(e)}")
                transaction['category'] = 'Other'
                transaction['confidence_score'] = 0.1
                transaction['categorization_method'] = 'error'
                categorized_transactions.append(transaction)
        
        return categorized_transactions
    
    @Tool
    def validate_and_refine_categories(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and refine categorization results"""
        refined_transactions = []
        
        for transaction in transactions:
            try:
                # Apply business rules
                refined_category = self._apply_business_rules(transaction)
                if refined_category != transaction.get('category'):
                    transaction['category'] = refined_category
                    transaction['confidence_score'] = max(0.8, transaction.get('confidence_score', 0.5))
                    transaction['refinement_applied'] = True
                
                # Validate category exists
                valid_categories = [
                    'Food & Dining', 'Groceries', 'Transportation', 'Entertainment',
                    'Utilities', 'Shopping', 'Healthcare', 'Education', 'Travel',
                    'Investment', 'Salary', 'Business', 'Rent/Mortgage', 'Insurance',
                    'Fuel', 'ATM/Cash', 'Transfer', 'Fees & Charges', 'Other'
                ]
                
                if transaction.get('category') not in valid_categories:
                    transaction['category'] = 'Other'
                
                refined_transactions.append(transaction)
                
            except Exception as e:
                logger.warning(f"Failed to refine transaction: {str(e)}")
                transaction['category'] = transaction.get('category', 'Other')
                refined_transactions.append(transaction)
        
        return refined_transactions
    
    def _rule_based_categorization(self, description: str) -> Dict[str, Any]:
        """Rule-based categorization using pattern matching"""
        description_lower = description.lower()
        best_match = None
        best_score = 0
        
        for category, patterns in self.category_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, description_lower):
                    # Weight longer matches more heavily
                    match_length = len(re.search(pattern, description_lower).group(0))
                    score += match_length / len(description_lower)
            
            if score > best_score:
                best_score = score
                best_match = category
        
        confidence = min(0.95, best_score * 2)  # Scale confidence
        
        if best_match and confidence > 0.3:
            return {
                'category': best_match,
                'confidence': confidence,
                'reasoning': f'Pattern matching: {description}'
            }
        else:
            return {
                'category': 'Other',
                'confidence': 0.2,
                'reasoning': 'No clear pattern match found'
            }
    
    def _apply_business_rules(self, transaction: Dict[str, Any]) -> str:
        """Apply business logic rules for categorization"""
        description = transaction.get('description', '').lower()
        amount = transaction.get('amount', 0)
        transaction_type = transaction.get('transaction_type', '')
        current_category = transaction.get('category', 'Other')
        
        # Rule 1: Large credit amounts are likely salary
        if transaction_type == 'credit' and amount > 25000:
            if any(keyword in description for keyword in ['salary', 'pay', 'wage', 'income']):
                return 'Salary'
        
        # Rule 2: ATM withdrawals
        if 'atm' in description or 'cash withdrawal' in description:
            return 'ATM/Cash'
        
        # Rule 3: UPI transactions
        if any(keyword in description for keyword in ['upi', 'gpay', 'paytm', 'phonepe']):
            # Keep existing category if it's specific, otherwise mark as transfer
            if current_category == 'Other':
                return 'Transfer'
        
        # Rule 4: EMI payments
        if 'emi' in description or 'installment' in description:
            if 'home' in description or 'house' in description:
                return 'Rent/Mortgage'
            elif 'car' in description or 'bike' in description:
                return 'Transportation'
        
        # Rule 5: Recurring payments
        if any(keyword in description for keyword in ['monthly', 'annual', 'subscription']):
            if current_category == 'Other':
                return 'Utilities'
        
        # Rule 6: Small amounts in convenience stores
        if amount < 500 and any(keyword in description for keyword in ['store', '7-eleven', 'convenience']):
            return 'Groceries'
        
        return current_category

# Create tool instance
categorization_tools = CategorizationTools()