"""
Data processing utilities for Finance Manager

This module provides comprehensive data processing capabilities including:
- Transaction data processing and normalization
- Date and time processing utilities
- Amount and currency processing
- Statistical calculations
- Data validation and cleaning
- Text normalization and cleaning
"""

import re
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
import unicodedata
from collections import Counter, defaultdict

class DateProcessor:
    """Advanced date processing utilities"""
    
    COMMON_DATE_FORMATS = [
        '%Y-%m-%d',     # 2024-01-15
        '%d-%m-%Y',     # 15-01-2024
        '%m-%d-%Y',     # 01-15-2024
        '%Y/%m/%d',     # 2024/01/15
        '%d/%m/%Y',     # 15/01/2024
        '%m/%d/%Y',     # 01/15/2024
        '%d-%m-%y',     # 15-01-24
        '%m-%d-%y',     # 01-15-24
        '%y-%m-%d',     # 24-01-15
        '%d/%m/%y',     # 15/01/24
        '%m/%d/%y',     # 01/15/24
        '%y/%m/%d',     # 24/01/15
        '%d %b %Y',     # 15 Jan 2024
        '%d %B %Y',     # 15 January 2024
        '%b %d, %Y',    # Jan 15, 2024
        '%B %d, %Y',    # January 15, 2024
    ]
    
    MONTH_NAMES = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12
    }
    
    @classmethod
    def parse_date(cls, date_string: Union[str, datetime, date]) -> Optional[datetime]:
        """
        Parse date from various formats
        
        Args:
            date_string: Date in string or datetime format
            
        Returns:
            Parsed datetime object or None if parsing fails
        """
        if isinstance(date_string, datetime):
            return date_string
        
        if isinstance(date_string, date):
            return datetime.combine(date_string, datetime.min.time())
        
        if not date_string or pd.isna(date_string):
            return None
        
        date_str = str(date_string).strip()
        if not date_str:
            return None
        
        # Try common formats
        for fmt in cls.COMMON_DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Try pandas date parser as fallback
        try:
            parsed = pd.to_datetime(date_str, errors='coerce')
            if pd.notna(parsed):
                return parsed.to_pydatetime()
        except:
            pass
        
        # Try manual parsing for Indian formats
        return cls._parse_indian_date_format(date_str)
    
    @classmethod
    def _parse_indian_date_format(cls, date_str: str) -> Optional[datetime]:
        """Parse Indian-specific date formats"""
        try:
            # Handle dd-mm-yyyy and similar formats
            patterns = [
                r'(\d{1,2})-(\d{1,2})-(\d{4})',  # dd-mm-yyyy
                r'(\d{1,2})/(\d{1,2})/(\d{4})',  # dd/mm/yyyy
                r'(\d{1,2})\.(\d{1,2})\.(\d{4})', # dd.mm.yyyy
            ]
            
            for pattern in patterns:
                match = re.match(pattern, date_str)
                if match:
                    day, month, year = map(int, match.groups())
                    return datetime(year, month, day)
            
        except (ValueError, TypeError):
            pass
        
        return None
    
    @classmethod
    def format_date(cls, date_obj: datetime, format_str: str = '%Y-%m-%d') -> str:
        """Format datetime object to string"""
        if not date_obj:
            return ''
        return date_obj.strftime(format_str)
    
    @classmethod
    def get_date_range(cls, transactions: List[Dict[str, Any]]) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Get date range from transactions"""
        dates = []
        
        for trans in transactions:
            date_obj = cls.parse_date(trans.get('date'))
            if date_obj:
                dates.append(date_obj)
        
        if not dates:
            return None, None
        
        return min(dates), max(dates)
    
    @classmethod
    def validate_date_range(cls, start_date: datetime, end_date: datetime, max_days: int = 365) -> Tuple[bool, Optional[str]]:
        """Validate date range"""
        if start_date > end_date:
            return False, "Start date cannot be after end date"
        
        if (end_date - start_date).days > max_days:
            return False, f"Date range cannot exceed {max_days} days"
        
        if start_date > datetime.now():
            return False, "Start date cannot be in the future"
        
        return True, None


class AmountProcessor:
    """Advanced amount and currency processing utilities"""
    
    CURRENCY_SYMBOLS = {
        '₹': 'INR',
        '$': 'USD',
        '€': 'EUR',
        '£': 'GBP',
        '¥': 'JPY'
    }
    
    @classmethod
    def parse_amount(cls, amount_str: Union[str, int, float, Decimal]) -> Optional[float]:
        """
        Parse amount from various formats
        
        Args:
            amount_str: Amount in various formats
            
        Returns:
            Parsed amount as float or None if parsing fails
        """
        if isinstance(amount_str, (int, float)):
            return float(amount_str) if not np.isnan(amount_str) else None
        
        if isinstance(amount_str, Decimal):
            return float(amount_str)
        
        if not amount_str or pd.isna(amount_str):
            return None
        
        amount_str = str(amount_str).strip()
        if not amount_str:
            return None
        
        try:
            # Remove currency symbols and common formatting
            cleaned = cls._clean_amount_string(amount_str)
            
            # Handle negative amounts
            is_negative = cleaned.startswith('-') or '(' in amount_str
            cleaned = cleaned.lstrip('-').strip('()')
            
            # Parse the cleaned string
            amount = float(cleaned)
            
            return -amount if is_negative else amount
            
        except (ValueError, TypeError):
            return None
    
    @classmethod
    def _clean_amount_string(cls, amount_str: str) -> str:
        """Clean amount string for parsing"""
        # Remove currency symbols
        for symbol in cls.CURRENCY_SYMBOLS.keys():
            amount_str = amount_str.replace(symbol, '')
        
        # Remove common formatting
        amount_str = amount_str.replace(',', '')  # Remove thousands separators
        amount_str = amount_str.replace(' ', '')   # Remove spaces
        amount_str = re.sub(r'[^\d.-]', '', amount_str)  # Keep only digits, dots, and minus
        
        return amount_str
    
    @classmethod
    def format_currency(cls, amount: float, currency: str = 'INR', include_symbol: bool = True) -> str:
        """Format amount as currency string"""
        if amount is None:
            return ''
        
        # Format with Indian numbering system for INR
        if currency == 'INR':
            return cls._format_indian_currency(amount, include_symbol)
        else:
            symbol = '₹' if currency == 'INR' and include_symbol else ''
            return f"{symbol}{amount:,.2f}"
    
    @classmethod
    def _format_indian_currency(cls, amount: float, include_symbol: bool = True) -> str:
        """Format amount in Indian numbering system"""
        symbol = '₹' if include_symbol else ''
        
        if amount < 0:
            return f"-{symbol}{cls._format_indian_currency(abs(amount), False)}"
        
        # Indian numbering: xx,xx,xxx.xx
        amount_str = f"{amount:.2f}"
        integer_part, decimal_part = amount_str.split('.')
        
        if len(integer_part) > 3:
            # Add commas in Indian style
            last_three = integer_part[-3:]
            remaining = integer_part[:-3]
            
            formatted = last_three
            while remaining:
                if len(remaining) >= 2:
                    formatted = remaining[-2:] + ',' + formatted
                    remaining = remaining[:-2]
                else:
                    formatted = remaining + ',' + formatted
                    break
        else:
            formatted = integer_part
        
        return f"{symbol}{formatted}.{decimal_part}"
    
    @classmethod
    def round_amount(cls, amount: float, precision: int = 2) -> float:
        """Round amount to specified precision"""
        if amount is None:
            return 0.0
        return round(float(amount), precision)


class TransactionProcessor:
    """Advanced transaction processing utilities"""
    
    TRANSACTION_TYPES = {'credit', 'debit', 'transfer'}
    
    @classmethod
    def normalize_transaction(cls, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize transaction data
        
        Args:
            transaction: Raw transaction dictionary
            
        Returns:
            Normalized transaction dictionary
        """
        normalized = transaction.copy()
        
        # Normalize date
        if 'date' in normalized:
            date_obj = DateProcessor.parse_date(normalized['date'])
            normalized['date'] = DateProcessor.format_date(date_obj) if date_obj else ''
        
        # Normalize amount
        if 'amount' in normalized:
            amount = AmountProcessor.parse_amount(normalized['amount'])
            normalized['amount'] = amount if amount is not None else 0.0
        
        # Normalize description
        if 'description' in normalized:
            normalized['description'] = normalize_text(normalized['description'])
        
        # Normalize transaction type
        if 'type' in normalized:
            trans_type = str(normalized['type']).lower().strip()
            if trans_type in cls.TRANSACTION_TYPES:
                normalized['type'] = trans_type
            else:
                # Try to infer type from amount or description
                normalized['type'] = cls._infer_transaction_type(normalized)
        
        return normalized
    
    @classmethod
    def _infer_transaction_type(cls, transaction: Dict[str, Any]) -> str:
        """Infer transaction type from transaction data"""
        description = str(transaction.get('description', '')).lower()
        amount = transaction.get('amount', 0)
        
        # Check for credit indicators
        credit_keywords = ['credit', 'deposit', 'salary', 'income', 'refund', 'cashback']
        if any(keyword in description for keyword in credit_keywords):
            return 'credit'
        
        # Check for transfer indicators
        transfer_keywords = ['transfer', 'neft', 'rtgs', 'imps', 'upi/']
        if any(keyword in description for keyword in transfer_keywords):
            return 'transfer'
        
        # Default to debit for negative amounts or general transactions
        return 'debit' if amount >= 0 else 'credit'
    
    @classmethod
    def validate_transaction(cls, transaction: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate transaction data
        
        Args:
            transaction: Transaction dictionary
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Required fields
        required_fields = ['date', 'description', 'amount', 'type']
        for field in required_fields:
            if field not in transaction or transaction[field] is None:
                errors.append(f"Missing required field: {field}")
        
        # Validate date
        if 'date' in transaction:
            date_obj = DateProcessor.parse_date(transaction['date'])
            if not date_obj:
                errors.append("Invalid date format")
        
        # Validate amount
        if 'amount' in transaction:
            amount = AmountProcessor.parse_amount(transaction['amount'])
            if amount is None:
                errors.append("Invalid amount")
            elif amount < 0:
                errors.append("Amount cannot be negative")
        
        # Validate description
        if 'description' in transaction:
            desc = str(transaction['description']).strip()
            if not desc:
                errors.append("Description cannot be empty")
        
        # Validate transaction type
        if 'type' in transaction:
            trans_type = str(transaction['type']).lower()
            if trans_type not in cls.TRANSACTION_TYPES:
                errors.append(f"Invalid transaction type: {trans_type}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def group_transactions_by_date(cls, transactions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group transactions by date"""
        grouped = defaultdict(list)
        
        for transaction in transactions:
            date_str = transaction.get('date', '')
            if date_str:
                grouped[date_str].append(transaction)
        
        return dict(grouped)
    
    @classmethod
    def filter_transactions_by_amount(cls, transactions: List[Dict[str, Any]], 
                                    min_amount: Optional[float] = None,
                                    max_amount: Optional[float] = None) -> List[Dict[str, Any]]:
        """Filter transactions by amount range"""
        filtered = []
        
        for transaction in transactions:
            amount = transaction.get('amount', 0)
            
            if min_amount is not None and amount < min_amount:
                continue
            
            if max_amount is not None and amount > max_amount:
                continue
            
            filtered.append(transaction)
        
        return filtered


class StatisticsCalculator:
    """Statistical calculations for financial data"""
    
    @classmethod
    def calculate_basic_stats(cls, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate basic transaction statistics"""
        if not transactions:
            return cls._empty_stats()
        
        amounts = [t.get('amount', 0) for t in transactions]
        credit_amounts = [t.get('amount', 0) for t in transactions if t.get('type') == 'credit']
        debit_amounts = [t.get('amount', 0) for t in transactions if t.get('type') == 'debit']
        
        stats = {
            'total_transactions': len(transactions),
            'total_amount': sum(amounts),
            'average_amount': np.mean(amounts) if amounts else 0,
            'median_amount': np.median(amounts) if amounts else 0,
            'max_amount': max(amounts) if amounts else 0,
            'min_amount': min(amounts) if amounts else 0,
            'std_amount': np.std(amounts) if amounts else 0,
            
            'total_credits': len(credit_amounts),
            'total_credit_amount': sum(credit_amounts),
            'average_credit': np.mean(credit_amounts) if credit_amounts else 0,
            
            'total_debits': len(debit_amounts),
            'total_debit_amount': sum(debit_amounts),
            'average_debit': np.mean(debit_amounts) if debit_amounts else 0,
        }
        
        # Calculate additional ratios
        if stats['total_credit_amount'] > 0:
            stats['savings_rate'] = (stats['total_credit_amount'] - stats['total_debit_amount']) / stats['total_credit_amount'] * 100
        else:
            stats['savings_rate'] = 0
        
        return stats
    
    @classmethod
    def _empty_stats(cls) -> Dict[str, Any]:
        """Return empty statistics structure"""
        return {
            'total_transactions': 0,
            'total_amount': 0,
            'average_amount': 0,
            'median_amount': 0,
            'max_amount': 0,
            'min_amount': 0,
            'std_amount': 0,
            'total_credits': 0,
            'total_credit_amount': 0,
            'average_credit': 0,
            'total_debits': 0,
            'total_debit_amount': 0,
            'average_debit': 0,
            'savings_rate': 0
        }
    
    @classmethod
    def calculate_category_stats(cls, category_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate category-wise statistics"""
        if not category_summary:
            return {}
        
        categories = list(category_summary.keys())
        amounts = [cat_data['total_amount'] for cat_data in category_summary.values()]
        transaction_counts = [cat_data['transaction_count'] for cat_data in category_summary.values()]
        
        total_amount = sum(amounts)
        
        stats = {
            'total_categories': len(categories),
            'top_category': categories[amounts.index(max(amounts))] if amounts else '',
            'top_category_amount': max(amounts) if amounts else 0,
            'least_category': categories[amounts.index(min(amounts))] if amounts else '',
            'least_category_amount': min(amounts) if amounts else 0,
            'average_category_amount': np.mean(amounts) if amounts else 0,
            'total_spending': total_amount,
            'most_frequent_category': categories[transaction_counts.index(max(transaction_counts))] if transaction_counts else ''
        }
        
        return stats


class DataProcessor:
    """Main data processor combining all utilities"""
    
    @classmethod
    def process_transaction_batch(cls, raw_transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a batch of raw transactions
        
        Args:
            raw_transactions: List of raw transaction dictionaries
            
        Returns:
            Processing results with normalized transactions and statistics
        """
        result = {
            'success': True,
            'processed_transactions': [],
            'invalid_transactions': [],
            'statistics': {},
            'errors': [],
            'warnings': []
        }
        
        try:
            for i, raw_transaction in enumerate(raw_transactions):
                try:
                    # Normalize transaction
                    normalized = TransactionProcessor.normalize_transaction(raw_transaction)
                    
                    # Validate transaction
                    is_valid, validation_errors = TransactionProcessor.validate_transaction(normalized)
                    
                    if is_valid:
                        result['processed_transactions'].append(normalized)
                    else:
                        normalized['validation_errors'] = validation_errors
                        result['invalid_transactions'].append(normalized)
                        result['warnings'].extend([f"Transaction {i+1}: {error}" for error in validation_errors])
                
                except Exception as e:
                    result['errors'].append(f"Error processing transaction {i+1}: {str(e)}")
                    result['invalid_transactions'].append({
                        'original': raw_transaction,
                        'error': str(e)
                    })
            
            # Calculate statistics
            result['statistics'] = StatisticsCalculator.calculate_basic_stats(result['processed_transactions'])
            
            # Update success status
            result['success'] = len(result['processed_transactions']) > 0
            
        except Exception as e:
            result['success'] = False
            result['errors'].append(f"Batch processing error: {str(e)}")
        
        return result


# Utility functions
def normalize_text(text: str, max_length: int = 200) -> str:
    """
    Normalize text by cleaning and standardizing
    
    Args:
        text: Input text
        max_length: Maximum length of normalized text
        
    Returns:
        Normalized text
    """
    if not text:
        return ''
    
    # Convert to string and strip
    text = str(text).strip()
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length].strip()
    
    return text


def clean_description(description: str) -> str:
    """
    Clean transaction description for better categorization
    
    Args:
        description: Raw transaction description
        
    Returns:
        Cleaned description
    """
    if not description:
        return ''
    
    # Normalize text
    cleaned = normalize_text(description)
    
    # Remove transaction IDs and reference numbers
    cleaned = re.sub(r'\b\d{6,}\b', '', cleaned)  # Remove long numbers
    cleaned = re.sub(r'/[A-Z0-9]{10,}', '', cleaned)  # Remove reference codes
    
    # Clean UPI transaction descriptions
    if 'UPI/' in cleaned:
        # Extract merchant name from UPI string
        upi_pattern = r'UPI/([^/]+)'
        match = re.search(upi_pattern, cleaned)
        if match:
            merchant = match.group(1).strip()
            if merchant and len(merchant) > 2:
                cleaned = merchant
    
    # Remove common bank prefixes
    bank_prefixes = ['NEFT', 'RTGS', 'IMPS', 'ACH', 'CMS']
    for prefix in bank_prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip('/ -')
    
    # Final cleanup
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned


def parse_amount(amount_str: Union[str, int, float]) -> Optional[float]:
    """Parse amount from string - wrapper for AmountProcessor"""
    return AmountProcessor.parse_amount(amount_str)


def format_currency(amount: float, currency: str = 'INR') -> str:
    """Format amount as currency - wrapper for AmountProcessor"""
    return AmountProcessor.format_currency(amount, currency)


def calculate_percentage(part: float, total: float) -> float:
    """Calculate percentage with safe division"""
    if total == 0:
        return 0.0
    return (part / total) * 100