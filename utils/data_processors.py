"""
Data processing utilities for Finance Manager Categorizer

This module provides comprehensive data processing capabilities for
financial transaction data including cleaning, validation, transformation,
and analysis utilities.
"""

import re
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
import statistics
from decimal import Decimal, InvalidOperation
from loguru import logger

@dataclass
class DataQualityMetrics:
    """Data quality metrics for financial data"""
    total_records: int
    valid_records: int
    missing_values: int
    duplicate_records: int
    data_quality_score: float
    issues: List[str]
    warnings: List[str]

class TransactionDataProcessor:
    """Processor for financial transaction data"""
    
    # Indian currency patterns
    CURRENCY_PATTERNS = [
        r'₹?\s*([0-9,]+\.?\d*)',  # Indian Rupee with commas
        r'INR\s*([0-9,]+\.?\d*)',  # INR format
        r'Rs\.?\s*([0-9,]+\.?\d*)',  # Rs. format
        r'([0-9,]+\.?\d*)\s*INR',  # Amount followed by INR
    ]
    
    # Date patterns for Indian formats
    DATE_PATTERNS = [
        r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b',  # DD/MM/YYYY or MM/DD/YYYY
        r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',    # YYYY/MM/DD
        r'\b(\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4})\b',  # DD/MMM/YYYY
        r'\b([A-Za-z]{3}\s+\d{1,2},?\s+\d{4})\b',   # MMM DD, YYYY
    ]
    
    def __init__(self):
        """Initialize the data processor"""
        self.processed_data = {}
        self.quality_metrics = None
        
    def clean_transaction_data(self, data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], DataQualityMetrics]:
        """
        Clean and standardize transaction data
        """
        try:
            cleaned_data = []
            issues = []
            warnings = []
            duplicates_count = 0
            missing_values_count = 0
            
            seen_transactions = set()
            
            for i, record in enumerate(data):
                try:
                    cleaned_record = self._clean_single_transaction(record, i)
                    
                    if cleaned_record is None:
                        issues.append(f"Record {i+1}: Could not clean transaction")
                        continue
                    
                    transaction_key = self._generate_transaction_key(cleaned_record)
                    if transaction_key in seen_transactions:
                        duplicates_count += 1
                        warnings.append(f"Record {i+1}: Potential duplicate transaction")
                        continue
                    
                    seen_transactions.add(transaction_key)
                    
                    missing_count = sum(1 for v in cleaned_record.values() 
                                      if v is None or (isinstance(v, str) and v.strip() == ''))
                    missing_values_count += missing_count
                    
                    if missing_count > 0:
                        warnings.append(f"Record {i+1}: {missing_count} missing values")
                    
                    cleaned_data.append(cleaned_record)
                    
                except Exception as e:
                    issues.append(f"Record {i+1}: {str(e)}")
                    logger.warning(f"Failed to clean record {i+1}: {str(e)}")
            
            total_records = len(data)
            valid_records = len(cleaned_data)
            quality_score = (valid_records / total_records * 100) if total_records > 0 else 0
            
            if missing_values_count > 0:
                quality_score -= min(10, (missing_values_count / total_records) * 50)
            
            if duplicates_count > 0:
                quality_score -= min(5, (duplicates_count / total_records) * 25)
            
            quality_metrics = DataQualityMetrics(
                total_records=total_records,
                valid_records=valid_records,
                missing_values=missing_values_count,
                duplicate_records=duplicates_count,
                data_quality_score=max(0, min(100, quality_score)),
                issues=issues,
                warnings=warnings
            )
            
            self.quality_metrics = quality_metrics
            logger.info(f"Data cleaning completed: {valid_records}/{total_records} records valid")
            
            return cleaned_data, quality_metrics
            
        except Exception as e:
            logger.error(f"Data cleaning failed: {str(e)}")
            raise
    
    def _clean_single_transaction(self, record: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
        """Clean a single transaction record"""
        try:
            cleaned = {}
            
            date_value = record.get('date', '')
            cleaned_date = self._clean_date(date_value)
            if cleaned_date is None:
                logger.warning(f"Record {index+1}: Invalid date '{date_value}'")
                return None
            cleaned['date'] = cleaned_date
            
            description = record.get('description', '')
            cleaned['description'] = self._clean_description(description)
            if not cleaned['description']:
                logger.warning(f"Record {index+1}: Empty description")
                return None
            
            amount_value = record.get('amount', '')
            cleaned_amount = self._clean_amount(amount_value)
            if cleaned_amount is None:
                logger.warning(f"Record {index+1}: Invalid amount '{amount_value}'")
                return None
            cleaned['amount'] = cleaned_amount
            
            type_value = record.get('type', record.get('transaction_type', ''))
            cleaned['transaction_type'] = self._clean_transaction_type(type_value, cleaned_amount)
            
            balance_value = record.get('balance', record.get('running_balance', ''))
            cleaned['balance'] = self._clean_balance(balance_value)
            
            cleaned['original_index'] = index
            cleaned['cleaned_at'] = datetime.now().isoformat()
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Failed to clean record {index+1}: {str(e)}")
            return None
    
    def _clean_date(self, date_value: Any) -> Optional[datetime]:
        """Clean and parse date value"""
        if not date_value:
            return None
        
        date_str = str(date_value).strip()
        if not date_str:
            return None
        
        try:
            parsed = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
            if pd.notna(parsed):
                return parsed.to_pydatetime()
        except:
            pass
        
        for pattern in self.DATE_PATTERNS:
            matches = re.findall(pattern, date_str)
            if matches:
                date_formats = [
                    '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y',
                    '%Y/%m/%d', '%Y-%m-%d',
                    '%d/%b/%Y', '%d-%b-%Y',
                    '%b %d, %Y', '%B %d, %Y'
                ]
                for fmt in date_formats:
                    try:
                        return datetime.strptime(matches[0], fmt)
                    except ValueError:
                        continue
        return None
    
    def _clean_description(self, description: Any) -> str:
        """Clean and standardize transaction description"""
        if not description:
            return ""
        desc = str(description).strip()
        desc = re.sub(r'\s+', ' ', desc)
        return desc
    
    def _clean_amount(self, amount_value: Any) -> Optional[Decimal]:
        """Clean and parse amount value"""
        if amount_value is None:
            return None
        
        amount_str = str(amount_value).replace(',', '').strip()
        
        for pattern in self.CURRENCY_PATTERNS:
            match = re.search(pattern, amount_str)
            if match:
                amount_str = match.group(1).replace(',', '')
                break
        
        try:
            return Decimal(amount_str)
        except (InvalidOperation, ValueError):
            return None
    
    def _clean_transaction_type(self, type_value: Any, amount: Decimal) -> str:
        """Standardize transaction type"""
        if not type_value:
            return "credit" if amount >= 0 else "debit"
        
        t = str(type_value).lower()
        if any(word in t for word in ["debit", "withdraw", "payment", "dr"]):
            return "debit"
        if any(word in t for word in ["credit", "deposit", "cr"]):
            return "credit"
        
        return "credit" if amount >= 0 else "debit"
    
    def _clean_balance(self, balance_value: Any) -> Optional[Decimal]:
        """Clean and parse balance value"""
        if not balance_value:
            return None
        
        balance_str = str(balance_value).replace(',', '').strip()
        
        for pattern in self.CURRENCY_PATTERNS:
            match = re.search(pattern, balance_str)
            if match:
                balance_str = match.group(1).replace(',', '')
                break
        
        try:
            return Decimal(balance_str)
        except (InvalidOperation, ValueError):
            return None
    
    def _generate_transaction_key(self, record: Dict[str, Any]) -> str:
        """Generate a unique key for a transaction to detect duplicates"""
        return f"{record.get('date')}_{record.get('description')}_{record.get('amount')}_{record.get('transaction_type')}"
