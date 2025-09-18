import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import pdfplumber
import PyPDF2
from agno.tools import tool
from loguru import logger


class FileExtractionTools:
    """Custom tools for extracting transaction data from various file formats"""
    
    
    def extract_csv_data(self, file_path: str) -> Dict[str, Any]:
        """Extract transaction data from CSV files"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise Exception("Could not read CSV with any encoding")
            
            # Common column name variations
            date_columns = ['date', 'transaction_date', 'txn_date', 'value_date', 'posting_date']
            desc_columns = ['description', 'transaction_description', 'particulars', 'narration', 'details']
            amount_columns = ['amount', 'transaction_amount', 'debit', 'credit', 'withdrawal', 'deposit']
            balance_columns = ['balance', 'running_balance', 'available_balance', 'closing_balance']
            
            # Find matching columns (case-insensitive)
            df_columns_lower = [col.lower() for col in df.columns]
            
            date_col = self._find_column(df_columns_lower, date_columns, df.columns)
            desc_col = self._find_column(df_columns_lower, desc_columns, df.columns)
            amount_col = self._find_column(df_columns_lower, amount_columns, df.columns)
            balance_col = self._find_column(df_columns_lower, balance_columns, df.columns)
            
            if not all([date_col, desc_col, amount_col]):
                raise Exception("Required columns not found in CSV")
            
            # Process the data
            transactions = []
            for _, row in df.iterrows():
                try:
                    # Parse date
                    date_str = str(row[date_col])
                    parsed_date = self._parse_date(date_str)
                    
                    # Parse amount and determine type
                    amount_str = str(row[amount_col]).replace(',', '').replace('₹', '').strip()
                    amount = abs(float(amount_str))
                    
                    # Determine transaction type
                    is_debit = '-' in str(row[amount_col]) or amount_str.startswith('-')
                    trans_type = 'debit' if is_debit else 'credit'
                    
                    # Parse balance if available
                    balance = None
                    if balance_col:
                        try:
                            balance_str = str(row[balance_col]).replace(',', '').replace('₹', '').strip()
                            balance = float(balance_str)
                        except:
                            balance = None
                    
                    transaction = {
                        'date': parsed_date.isoformat(),
                        'description': str(row[desc_col]).strip(),
                        'amount': amount,
                        'transaction_type': trans_type,
                        'balance': balance
                    }
                    transactions.append(transaction)
                    
                except Exception as e:
                    logger.warning(f"Skipping row due to parsing error: {str(e)}")
                    continue
            
            return {
                'success': True,
                'transactions': transactions,
                'total_count': len(transactions)
            }
            
        except Exception as e:
            logger.error(f"CSV extraction failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'transactions': []
            }
    
    
    def extract_excel_data(self, file_path: str) -> Dict[str, Any]:
        """Extract transaction data from Excel files"""
        try:
            # Try reading different sheets
            xl_file = pd.ExcelFile(file_path)
            sheet_names = xl_file.sheet_names
            
            # Try first sheet, or look for common sheet names
            target_sheets = ['transactions', 'statement', 'account', 'sheet1', sheet_names[0]]
            
            df = None
            for sheet in target_sheets:
                if sheet in sheet_names:
                    try:
                        df = pd.read_excel(file_path, sheet_name=sheet)
                        break
                    except:
                        continue
            
            if df is None:
                df = pd.read_excel(file_path)
            
            # Convert to CSV format for consistent processing
            temp_csv = file_path.replace('.xlsx', '.tmp.csv').replace('.xls', '.tmp.csv')
            df.to_csv(temp_csv, index=False)
            
            # Use CSV extraction logic
            result = self.extract_csv_data(temp_csv)
            
            # Clean up temp file
            if os.path.exists(temp_csv):
                os.remove(temp_csv)
            
            return result
            
        except Exception as e:
            logger.error(f"Excel extraction failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'transactions': []
            }
    
    
    def extract_pdf_data(self, file_path: str) -> Dict[str, Any]:
        """Extract transaction data from PDF bank statements"""
        try:
            transactions = []
            
            # Try pdfplumber first (better for tables)
            try:
                with pdfplumber.open(file_path) as pdf:
                    all_text = ""
                    for page in pdf.pages:
                        tables = page.extract_tables()
                        if tables:
                            # Process tables
                            for table in tables:
                                transactions.extend(self._process_pdf_table(table))
                        else:
                            # Extract text if no tables
                            all_text += page.extract_text() + "\n"
                    
                    # If no tables found, try text extraction
                    if not transactions and all_text:
                        transactions = self._extract_from_pdf_text(all_text)
                        
            except Exception as e:
                logger.warning(f"pdfplumber failed, trying PyPDF2: {str(e)}")
                
                # Fallback to PyPDF2
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    all_text = ""
                    for page in pdf_reader.pages:
                        all_text += page.extract_text() + "\n"
                    
                    transactions = self._extract_from_pdf_text(all_text)
            
            return {
                'success': True,
                'transactions': transactions,
                'total_count': len(transactions)
            }
            
        except Exception as e:
            logger.error(f"PDF extraction failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'transactions': []
            }
    
    def _find_column(self, df_columns_lower: List[str], target_columns: List[str], original_columns: List[str]) -> Optional[str]:
        """Find matching column name"""
        for target in target_columns:
            if target in df_columns_lower:
                index = df_columns_lower.index(target)
                return original_columns[index]
        return None
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string into datetime object"""
        date_formats = [
            '%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y',
            '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y',
            '%d-%b-%Y', '%d-%B-%Y',
            '%d.%m.%Y', '%Y.%m.%d'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Cannot parse date: {date_str}")
    
    def _process_pdf_table(self, table: List[List[str]]) -> List[Dict[str, Any]]:
        """Process PDF table data"""
        transactions = []
        
        if not table or len(table) < 2:
            return transactions
        
        # Try to identify header row
        headers = [str(cell).lower().strip() if cell else '' for cell in table[0]]
        
        # Look for date, description, amount patterns
        date_pattern = re.compile(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b')
        amount_pattern = re.compile(r'[\d,]+\.?\d*')
        
        for row in table[1:]:
            if not row or len(row) < 3:
                continue
                
            try:
                # Find date column
                date_str = None
                description = ""
                amount = 0
                
                for i, cell in enumerate(row):
                    cell_str = str(cell).strip() if cell else ''
                    
                    if date_pattern.search(cell_str) and not date_str:
                        date_str = cell_str
                    elif re.search(r'[a-zA-Z]', cell_str) and len(cell_str) > 3:
                        description = cell_str
                    elif amount_pattern.search(cell_str.replace(',', '')):
                        try:
                            amount = abs(float(cell_str.replace(',', '').replace('₹', '')))
                        except:
                            pass
                
                if date_str and description and amount > 0:
                    parsed_date = self._parse_date(date_str)
                    
                    transaction = {
                        'date': parsed_date.isoformat(),
                        'description': description,
                        'amount': amount,
                        'transaction_type': 'debit',  # Default, will be refined later
                        'balance': None
                    }
                    transactions.append(transaction)
                    
            except Exception as e:
                logger.warning(f"Skipping PDF row due to parsing error: {str(e)}")
                continue
        
        return transactions
    
    def _extract_from_pdf_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract transactions from PDF text using regex patterns"""
        transactions = []
        
        # Common patterns for Indian bank statements
        patterns = [
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+([^0-9]+?)\s+([\d,]+\.?\d*)',
            r'(\d{1,2}-\w{3}-\d{4})\s+([^0-9]+?)\s+([\d,]+\.?\d*)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    date_str, description, amount_str = match.groups()
                    
                    parsed_date = self._parse_date(date_str)
                    amount = float(amount_str.replace(',', ''))
                    
                    transaction = {
                        'date': parsed_date.isoformat(),
                        'description': description.strip(),
                        'amount': amount,
                        'transaction_type': 'debit',
                        'balance': None
                    }
                    transactions.append(transaction)
                    
                except Exception as e:
                    logger.warning(f"Skipping text match due to parsing error: {str(e)}")
                    continue
        
        return transactions

# Create tool instance
file_extraction_tools = FileExtractionTools()