"""
Utility functions and helpers for Finance Manager

This module contains common utility functions used across the application:
- File handling utilities
- Data processing helpers  
- Validation functions
- Common constants and enums
- Helper functions for data transformation
"""

__version__ = "1.0.0"

from .file_handlers import (
    FileHandler,
    FileValidator,
    FileTypeDetector,
    secure_filename,
    get_file_extension,
    validate_file_size,
    create_upload_directory
)

from .data_processors import (
    DataProcessor,
    TransactionProcessor,
    DateProcessor,
    AmountProcessor,
    CurrencyFormatter,
    StatisticsCalculator,
    normalize_text,
    clean_description,
    parse_amount,
    format_currency
)

from .helpers import (
    generate_unique_id,
    get_current_timestamp,
    format_date,
    validate_date_range,
    calculate_percentage,
    round_amount,
    sanitize_string,
    log_performance
)

# Common constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
SUPPORTED_FILE_TYPES = ['.csv', '.xlsx', '.xls', '.pdf']
DEFAULT_CURRENCY = 'INR'
DATE_FORMAT = '%Y-%m-%d'
TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'

# Transaction categories
TRANSACTION_CATEGORIES = [
    "Food & Dining",
    "Transportation", 
    "Shopping",
    "Entertainment",
    "Bills & Utilities",
    "Healthcare",
    "Travel",
    "Education",
    "Groceries",
    "Income",
    "Transfer",
    "Investment",
    "Insurance",
    "ATM Withdrawal",
    "Bank Charges",
    "Other"
]

# UPI keywords for categorization
UPI_FOOD_KEYWORDS = ['zomato', 'swiggy', 'blinkit', 'starbucks', 'mcdonald', 'kfc', 'domino', 'pizza', 'restaurant', 'cafe', 'food', 'dining']
UPI_TRANSPORT_KEYWORDS = ['uber', 'ola', 'metro', 'pmpml', 'railway', 'bus', 'taxi', 'transport', 'fuel', 'petrol', 'diesel']
UPI_GROCERY_KEYWORDS = ['grocery', 'supermarket', 'bigbasket', 'grofers', 'store', 'mart']
UPI_ENTERTAINMENT_KEYWORDS = ['netflix', 'amazon prime', 'hotstar', 'spotify', 'youtube', 'movie', 'cinema', 'game', 'entertainment']
UPI_UTILITY_KEYWORDS = ['electricity', 'water', 'gas', 'internet', 'mobile', 'recharge', 'bill', 'utility']
UPI_INVESTMENT_KEYWORDS = ['indmoney', 'mutual fund', 'sip', 'investment', 'stock', 'equity', 'groww', 'zerodha']
UPI_SHOPPING_KEYWORDS = ['amazon', 'flipkart', 'myntra', 'shop', 'purchase', 'buy']

# Bank transaction patterns
BANK_PATTERNS = {
    'NEFT': ['neft', 'national electronic'],
    'RTGS': ['rtgs', 'real time gross'],
    'IMPS': ['imps', 'immediate payment'],
    'UPI': ['upi/', 'unified payment'],
    'ATM': ['atm', 'withdrawal', 'cash'],
    'SALARY': ['salary', 'pay', 'income'],
    'INTEREST': ['interest', 'saving', 'fd'],
    'CHARGES': ['charges', 'fee', 'penalty']
}

# Error messages
ERROR_MESSAGES = {
    'FILE_TOO_LARGE': 'File size exceeds maximum limit of {max_size}MB',
    'UNSUPPORTED_FORMAT': 'Unsupported file format. Please upload CSV, Excel, or PDF files',
    'INVALID_DATE': 'Invalid date format. Please use YYYY-MM-DD format',
    'INVALID_AMOUNT': 'Invalid amount. Please enter a valid number',
    'MISSING_REQUIRED_FIELD': 'Required field "{field}" is missing',
    'PROCESSING_ERROR': 'Error processing file: {error}',
    'AI_SERVICE_ERROR': 'AI service is temporarily unavailable',
    'CATEGORIZATION_FAILED': 'Failed to categorize transaction: {description}'
}

__all__ = [
    'FileHandler', 'FileValidator', 'FileTypeDetector',
    'DataProcessor', 'TransactionProcessor', 'DateProcessor', 'AmountProcessor',
    'CurrencyFormatter', 'StatisticsCalculator',
    'generate_unique_id', 'get_current_timestamp', 'format_date',
    'validate_date_range', 'calculate_percentage', 'round_amount',
    'sanitize_string', 'log_performance', 'secure_filename',
    'get_file_extension', 'validate_file_size', 'create_upload_directory',
    'normalize_text', 'clean_description', 'parse_amount', 'format_currency',
    'MAX_FILE_SIZE', 'SUPPORTED_FILE_TYPES', 'DEFAULT_CURRENCY',
    'DATE_FORMAT', 'TIMESTAMP_FORMAT', 'TRANSACTION_CATEGORIES',
    'UPI_FOOD_KEYWORDS', 'UPI_TRANSPORT_KEYWORDS', 'UPI_GROCERY_KEYWORDS',
    'UPI_ENTERTAINMENT_KEYWORDS', 'UPI_UTILITY_KEYWORDS', 'UPI_INVESTMENT_KEYWORDS',
    'UPI_SHOPPING_KEYWORDS', 'BANK_PATTERNS', 'ERROR_MESSAGES'
]