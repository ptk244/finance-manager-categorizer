"""
File processing service for handling CSV, Excel, and PDF files
"""
import io
import re
import csv
import PyPDF2
import pdfplumber
import pandas as pd
import structlog
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from pathlib import Path
from app.models.transaction import Transaction
from app.config import get_settings

logger = structlog.get_logger(__name__)


class FileProcessor:
    """
    Handles processing of various file formats to extract transaction data.
    Supports CSV, Excel (XLS/XLSX), and PDF formats with Indian bank statement patterns.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = logger.bind(service="FileProcessor")
        
        # Common column mapping patterns for Indian banks
        self.column_mappings = {
            'date': ['date', 'txn date', 'transaction date', 'value date', 'posted date', 'txn_date'],
            'description': ['description', 'narration', 'particulars', 'transaction details', 'remarks', 'reference'],
            'debit': ['debit', 'debit amount', 'withdrawal', 'dr', 'debit_amount'],
            'credit': ['credit', 'credit amount', 'deposit', 'cr', 'credit_amount'],
            'amount': ['amount', 'transaction amount', 'txn amount', 'amt'],
            'balance': ['balance', 'available balance', 'closing balance', 'running balance', 'balance_amount']
        }
        
        # Date formats commonly used in Indian bank statements
        self.date_formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',
            '%d/%m/%y', '%d-%m-%y', '%d.%m.%y',
            '%d %b %Y', '%d-%b-%Y', '%d %B %Y',
            '%Y-%m-%d', '%m/%d/%Y'
        ]
    
    def _create_transaction_safely(self, parsed_date, description, amount, txn_type, balance=None):
        """
        Safely create a Transaction object with proper validation
        """
        try:
            # Ensure all required fields are present and valid
            if not parsed_date:
                self.logger.debug("Skipping transaction: no valid date")
                return None
                
            if not description or str(description).strip() == '':
                description = "Transaction"
            else:
                description = str(description).strip()
                
            if not amount or amount <= 0:
                self.logger.debug("Skipping transaction: invalid amount", amount=amount)
                return None
                
            if txn_type not in ['debit', 'credit']:
                txn_type = 'debit'
            
            # Clean and validate balance
            clean_balance = None
            if balance is not None:
                try:
                    clean_balance = float(balance)
                except (ValueError, TypeError):
                    clean_balance = None
                    
            transaction = Transaction(
                transaction_date=parsed_date,
                description=description,
                amount=float(amount),
                type=txn_type,
                balance=clean_balance
            )
            
            return transaction
            
        except Exception as e:
            self.logger.debug("Failed to create transaction", error=str(e))
            return None
    
    async def process_file(self, file_content: bytes, filename: str) -> List[Transaction]:
        """
        Process uploaded file and extract transactions
        
        Args:
            file_content: Raw file content
            filename: Original filename
            
        Returns:
            List of extracted transactions
        """
        try:
            self.logger.info("Processing file", filename=filename, size=len(file_content))
            
            # Determine file type
            file_ext = Path(filename).suffix.lower()
            
            if file_ext == '.csv':
                return await self._process_csv(file_content)
            elif file_ext in ['.xlsx', '.xls']:
                return await self._process_excel(file_content, file_ext)
            elif file_ext == '.pdf':
                return await self._process_pdf(file_content)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
                
        except Exception as e:
            self.logger.error("File processing failed", filename=filename, error=str(e))
            raise
    
    async def _process_csv(self, file_content: bytes) -> List[Transaction]:
        """Process CSV file"""
        try:
            # Try different encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    content_str = file_content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError("Could not decode CSV file with any common encoding")
            
            # Try different delimiters
            for delimiter in [',', ';', '\t', '|']:
                try:
                    csv_reader = csv.DictReader(io.StringIO(content_str), delimiter=delimiter)
                    rows = list(csv_reader)
                    
                    if len(rows) > 0 and len(rows[0]) > 1:  # Valid CSV with multiple columns
                        return self._extract_transactions_from_rows(rows)
                        
                except Exception:
                    continue
            
            # If all delimiters fail, try pandas
            return await self._process_csv_with_pandas(file_content)
            
        except Exception as e:
            self.logger.error("CSV processing failed", error=str(e))
            raise ValueError(f"Failed to process CSV file: {str(e)}")
    
    async def _process_csv_with_pandas(self, file_content: bytes) -> List[Transaction]:
        """Process CSV using pandas with various configurations"""
        try:
            # Try different configurations
            configs = [
                {'encoding': 'utf-8', 'delimiter': ','},
                {'encoding': 'latin-1', 'delimiter': ','},
                {'encoding': 'utf-8', 'delimiter': ';'},
                {'encoding': 'cp1252', 'delimiter': ','},
            ]
            
            for config in configs:
                try:
                    df = pd.read_csv(io.BytesIO(file_content), **config)
                    if not df.empty and len(df.columns) > 1:
                        return self._extract_transactions_from_dataframe(df)
                except Exception:
                    continue
            
            raise ValueError("Could not process CSV with any configuration")
            
        except Exception as e:
            raise ValueError(f"Failed to process CSV with pandas: {str(e)}")
    
    async def _process_excel(self, file_content: bytes, file_ext: str) -> List[Transaction]:
        """Process Excel file"""
        try:
            # Read Excel file
            engine = 'openpyxl' if file_ext == '.xlsx' else 'xlrd'
            
            # Try to read the first sheet
            df = pd.read_excel(io.BytesIO(file_content), engine=engine)
            
            if df.empty:
                raise ValueError("Excel file appears to be empty")
            
            return self._extract_transactions_from_dataframe(df)
            
        except Exception as e:
            self.logger.error("Excel processing failed", error=str(e))
            raise ValueError(f"Failed to process Excel file: {str(e)}")
    
    async def _process_pdf(self, file_content: bytes) -> List[Transaction]:
        """Process PDF file"""
        try:
            self.logger.info("Processing PDF file")
            
            # Try with pdfplumber first (better for tables)
            try:
                transactions = await self._process_pdf_with_pdfplumber(file_content)
                if transactions:
                    return transactions
            except Exception as e:
                self.logger.warning("pdfplumber processing failed", error=str(e))
            
            # Fallback to PyPDF2
            try:
                transactions = await self._process_pdf_with_pypdf2(file_content)
                if transactions:
                    return transactions
            except Exception as e:
                self.logger.warning("PyPDF2 processing failed", error=str(e))
            
            raise ValueError("Could not extract transaction data from PDF")
            
        except Exception as e:
            self.logger.error("PDF processing failed", error=str(e))
            raise ValueError(f"Failed to process PDF file: {str(e)}")
    
    async def _process_pdf_with_pdfplumber(self, file_content: bytes) -> List[Transaction]:
        """Process PDF using pdfplumber"""
        transactions = []
        
        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                self.logger.info(f"Processing PDF with {len(pdf.pages)} pages")
                
                for page_num, page in enumerate(pdf.pages):
                    self.logger.debug(f"Processing page {page_num + 1}")
                    
                    # Try to extract tables first
                    tables = page.extract_tables() 
                    
                    page_transactions = []
                    
                    if tables:
                        self.logger.debug(f"Found {len(tables)} tables on page {page_num + 1}")
                        
                        for table_num, table in enumerate(tables):
                            if not table or len(table) < 2:
                                continue
                            
                            self.logger.debug(f"Processing table {table_num + 1} with {len(table)} rows")
                            
                            try:
                                # Find the header row (might not be the first row)
                                header_row = None
                                data_start_index = 1
                                
                                for i, row in enumerate(table):
                                    if row and any(cell for cell in row if cell and isinstance(cell, str)):
                                        # Check if this looks like a header
                                        row_text = ' '.join(str(cell).lower() for cell in row if cell)
                                        if any(header_word in row_text for header_word in ['date', 'description', 'amount', 'debit', 'credit', 'balance']):
                                            header_row = row
                                            data_start_index = i + 1
                                            break
                                
                                if not header_row:
                                    # Use first row as header if no clear header found
                                    header_row = table[0]
                                    data_start_index = 1
                                
                                # Clean header row
                                headers = []
                                for cell in header_row:
                                    if cell:
                                        headers.append(str(cell).strip())
                                    else:
                                        headers.append("")
                                
                                self.logger.debug(f"Table headers: {headers}")
                                
                                # Convert table data to dictionaries
                                rows = []
                                for row in table[data_start_index:]:
                                    if not row or len(row) != len(headers):
                                        continue
                                    
                                    # Check if row has meaningful data
                                    if not any(cell and str(cell).strip() for cell in row):
                                        continue
                                    
                                    row_dict = {}
                                    for i, cell in enumerate(row):
                                        if i < len(headers):
                                            row_dict[headers[i]] = str(cell).strip() if cell else ""
                                    
                                    rows.append(row_dict)
                                
                                self.logger.debug(f"Extracted {len(rows)} data rows from table")
                                
                                # Extract transactions from rows
                                if rows:
                                    table_transactions = self._extract_transactions_from_rows(rows)
                                    page_transactions.extend(table_transactions)
                                    
                            except Exception as e:
                                self.logger.warning(f"Failed to extract from table {table_num + 1}: {str(e)}")
                                continue
                    
                    # If no transactions from tables, try text extraction
                    if not page_transactions:
                        text = page.extract_text()
                        if text:
                            self.logger.debug(f"Trying text extraction on page {page_num + 1}")
                            try:
                                text_transactions = self._extract_transactions_from_text(text)
                                page_transactions.extend(text_transactions)
                            except Exception as e:
                                self.logger.warning(f"Text extraction failed on page {page_num + 1}: {str(e)}")
                    
                    transactions.extend(page_transactions)
                    self.logger.debug(f"Page {page_num + 1}: extracted {len(page_transactions)} transactions")
                
        except Exception as e:
            self.logger.error(f"Error processing PDF with pdfplumber: {str(e)}")
            raise
        
        self.logger.info(f"PDF processing complete: extracted {len(transactions)} total transactions")
        return transactions
    
    async def _process_pdf_with_pypdf2(self, file_content: bytes) -> List[Transaction]:
        """Process PDF using PyPDF2"""
        transactions = []
        
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    try:
                        page_transactions = self._extract_transactions_from_text(text)
                        transactions.extend(page_transactions)
                    except Exception as e:
                        self.logger.warning(f"Failed to extract from PDF page: {str(e)}")
                        continue
        except Exception as e:
            self.logger.error(f"Error processing PDF with PyPDF2: {str(e)}")
            raise
        
        return transactions
    
    def _extract_transactions_from_text(self, text: str) -> List[Transaction]:
        """Extract transactions from raw text using pattern matching"""
        transactions = []
        
        # Common patterns for Indian bank statements
        patterns = [
            # Pattern 1: Date Description Debit Credit Balance (most common)
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            # Pattern 2: Date Description Amount Balance
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.{10,}?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            # Pattern 3: More flexible date and amount pattern
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+(\d+[,\d]*\.?\d*)',
            # Pattern 4: Date followed by text and numbers
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+([A-Za-z].*?)\s+(\d+\.?\d*)',
        ]
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:  # Skip very short lines
                continue
            
            # Skip header lines
            if any(header in line.lower() for header in ['date', 'description', 'debit', 'credit', 'balance', 'transaction', 'particulars']):
                continue
            
            # Try each pattern
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    try:
                        groups = match.groups()
                        
                        if len(groups) >= 3:
                            date_str = groups[0]
                            description = groups[1].strip()
                            
                            # Parse date
                            parsed_date = self._parse_date(date_str)
                            if not parsed_date:
                                continue
                            
                            # Clean description
                            description = re.sub(r'\s+', ' ', description)
                            if len(description) < 3:
                                description = "Transaction"
                            
                            # Extract amounts
                            amounts = []
                            for i in range(2, len(groups)):
                                amount = self._parse_amount(groups[i])
                                if amount > 0:
                                    amounts.append(amount)
                            
                            if not amounts:
                                continue
                            
                            # Determine transaction type and amount
                            if len(amounts) >= 3:  # Date, Desc, Debit, Credit, Balance
                                debit_amt = amounts[0]
                                credit_amt = amounts[1]
                                balance = amounts[2] if len(amounts) > 2 else None
                                
                                if debit_amt > 0:
                                    amount = debit_amt
                                    txn_type = 'debit'
                                elif credit_amt > 0:
                                    amount = credit_amt
                                    txn_type = 'credit'
                                else:
                                    continue
                            elif len(amounts) >= 2:  # Date, Desc, Amount, Balance
                                amount = amounts[0]
                                balance = amounts[1]
                                # Try to determine type from description or context
                                if any(word in description.lower() for word in ['deposit', 'credit', 'salary', 'transfer in']):
                                    txn_type = 'credit'
                                else:
                                    txn_type = 'debit'
                            else:  # Just amount
                                amount = amounts[0]
                                balance = None
                                txn_type = 'debit'  # Default
                            
                            transaction = self._create_transaction_safely(
                                parsed_date=parsed_date,
                                description=description,
                                amount=amount,
                                txn_type=txn_type,
                                balance=balance
                            )
                            
                            if transaction:
                                transactions.append(transaction)
                            break
                            
                    except Exception as e:
                        self.logger.debug("Failed to parse transaction from text", 
                                        line=line[:100], error=str(e))
                        continue
        
        # If no transactions found, try simpler extraction
        if not transactions:
            transactions = self._extract_simple_patterns(text)
        
        return transactions
    
    def _extract_simple_patterns(self, text: str) -> List[Transaction]:
        """Extract transactions using simpler patterns as fallback"""
        transactions = []
        
        # Very basic pattern - any line with date and amount
        simple_patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}).*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}).*?(\d+\.\d{2})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}).*?(\d+)',
        ]
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if len(line) < 8:  # Skip very short lines
                continue
                
            for pattern in simple_patterns:
                match = re.search(pattern, line)
                if match:
                    try:
                        date_str = match.group(1)
                        amount_str = match.group(2)
                        
                        parsed_date = self._parse_date(date_str)
                        if not parsed_date:
                            continue
                            
                        amount = self._parse_amount(amount_str)
                        if amount <= 0:
                            continue
                        
                        # Extract description (everything between date and amount)
                        description = line.replace(date_str, '').replace(amount_str, '').strip()
                        if not description or len(description) < 3:
                            description = "Transaction"
                        
                        transaction = self._create_transaction_safely(
                            parsed_date=parsed_date,
                            description=description,
                            amount=amount,
                            txn_type='debit',  # Default to debit
                            balance=None
                        )
                        
                        if transaction:
                            transactions.append(transaction)
                        break
                        
                    except Exception as e:
                        self.logger.debug("Failed to parse simple pattern", error=str(e))
                        continue
        
        return transactions
    
    def _extract_transactions_from_dataframe(self, df: pd.DataFrame) -> List[Transaction]:
        """Extract transactions from pandas DataFrame"""
        # Clean column names
        df.columns = df.columns.str.strip().str.lower()
        
        # Map columns to standard names
        column_mapping = self._map_columns(df.columns.tolist())
        
        if not column_mapping.get('date'):
            raise ValueError("Could not identify date column")
        
        transactions = []
        
        for _, row in df.iterrows():
            try:
                # Skip empty rows
                if row.isna().all():
                    continue
                
                # Extract date
                date_value = row.get(column_mapping['date'])
                if pd.isna(date_value):
                    continue
                
                parsed_date = self._parse_date(str(date_value))
                if not parsed_date:
                    continue
                
                # Extract description
                description = ""
                if column_mapping.get('description'):
                    description = str(row.get(column_mapping['description'], "")).strip()
                
                if not description or description == 'nan':
                    description = "Transaction"
                
                # Extract amount and type
                amount, txn_type = self._extract_amount_and_type(row, column_mapping)
                
                if amount == 0:
                    continue
                
                # Extract balance
                balance = None
                if column_mapping.get('balance'):
                    balance_value = row.get(column_mapping['balance'])
                    if not pd.isna(balance_value):
                        balance = self._parse_amount(str(balance_value))
                
                # Create transaction
                transaction = self._create_transaction_safely(
                    parsed_date=parsed_date,
                    description=description,
                    amount=amount,
                    txn_type=txn_type,
                    balance=balance
                )
                
                if transaction:
                    transactions.append(transaction)
                
            except Exception as e:
                self.logger.debug("Failed to process row", error=str(e))
                continue
        
        return transactions
    
    def _extract_transactions_from_rows(self, rows: List[Dict[str, Any]]) -> List[Transaction]:
        """Extract transactions from list of row dictionaries"""
        if not rows:
            return []
        
        # Clean and normalize column names
        cleaned_rows = []
        for row in rows:
            cleaned_row = {}
            for key, value in row.items():
                if key is not None:
                    clean_key = str(key).strip().lower()
                    cleaned_row[clean_key] = value
            if cleaned_row:  # Only add non-empty rows
                cleaned_rows.append(cleaned_row)
        
        if not cleaned_rows:
            return []
        
        # Map columns
        column_names = list(cleaned_rows[0].keys()) if cleaned_rows else []
        column_mapping = self._map_columns(column_names)
        
        self.logger.debug("Column mapping for transaction extraction", 
                         available_columns=column_names, 
                         mapping=column_mapping)
        
        # If we still can't find a date column, try to infer from data
        if not column_mapping.get('date'):
            self.logger.warning("No date column found, trying to infer from data")
            
            # Look for columns that contain date-like data
            for col_name in column_names:
                if cleaned_rows and col_name in cleaned_rows[0]:
                    sample_value = str(cleaned_rows[0][col_name])
                    if self._looks_like_date(sample_value):
                        column_mapping['date'] = col_name
                        self.logger.info(f"Inferred date column: {col_name}")
                        break
        
        if not column_mapping.get('date'):
            # Try to use the first column that might contain dates
            for row in cleaned_rows[:5]:  # Check first 5 rows
                for col_name, value in row.items():
                    if value and self._looks_like_date(str(value)):
                        column_mapping['date'] = col_name
                        self.logger.info(f"Found date column from data inspection: {col_name}")
                        break
                if column_mapping.get('date'):
                    break
        
        if not column_mapping.get('date'):
            self.logger.error("Could not identify date column", 
                            available_columns=column_names,
                            sample_data=cleaned_rows[0] if cleaned_rows else {})
            return []
        
        transactions = []
        
        for row in cleaned_rows:
            try:
                # Extract date
                date_value = row.get(column_mapping['date'])
                if not date_value or str(date_value).strip() == '':
                    continue
                
                parsed_date = self._parse_date(str(date_value))
                if not parsed_date:
                    continue
                
                # Extract description
                description = ""
                if column_mapping.get('description'):
                    desc_value = row.get(column_mapping['description'])
                    if desc_value:
                        description = str(desc_value).strip()
                
                if not description:
                    # Try to find any text column for description
                    for key, value in row.items():
                        if value and isinstance(value, str) and len(value.strip()) > 3:
                            if key != column_mapping.get('date') and not str(value).replace(',', '').replace('.', '').isdigit():
                                description = str(value).strip()
                                break
                    
                    if not description:
                        description = "Transaction"
                
                # Extract amount and type
                amount, txn_type = self._extract_amount_and_type(row, column_mapping)
                
                if amount == 0:
                    continue
                
                # Extract balance
                balance = None
                if column_mapping.get('balance'):
                    balance_value = row.get(column_mapping['balance'])
                    if balance_value:
                        balance = self._parse_amount(str(balance_value))
                
                # Create transaction
                transaction = self._create_transaction_safely(
                    parsed_date=parsed_date,
                    description=description,
                    amount=amount,
                    txn_type=txn_type,
                    balance=balance
                )
                
                if transaction:
                    transactions.append(transaction)
                
            except Exception as e:
                self.logger.debug("Failed to process row", row=str(row)[:200], error=str(e))
                continue
        
        return transactions
    
    def _looks_like_date(self, value: str) -> bool:
        """Check if a string value looks like a date"""
        if not value or not isinstance(value, str):
            return False
            
        value = value.strip()
        
        # Check for date patterns
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{2,4}[/-]\d{1,2}[/-]\d{1,2}',
            r'\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4}',
            r'\d{1,2}-[A-Za-z]{3}-\d{2,4}',
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, value):
                return True
        
        # Try parsing with common date formats
        for date_format in self.date_formats[:5]:  # Check most common formats
            try:
                datetime.strptime(value, date_format)
                return True
            except ValueError:
                continue
        
        return False
    
    def _map_columns(self, columns: List[str]) -> Dict[str, str]:
        """Map actual column names to standard field names"""
        mapping = {}
        
        # Normalize column names
        normalized_columns = [col.strip().lower().replace('_', ' ').replace('-', ' ') for col in columns]
        
        self.logger.debug("Mapping columns", original=columns, normalized=normalized_columns)
        
        # Find best matches for each field
        for field, patterns in self.column_mappings.items():
            best_match = None
            best_score = 0
            
            for i, col in enumerate(normalized_columns):
                for pattern in patterns:
                    # Check for exact match or substring match
                    if pattern == col:
                        score = 100  # Exact match gets highest score
                        if score > best_score:
                            best_score = score
                            best_match = columns[i]
                    elif pattern in col:
                        score = len(pattern) * 2  # Partial match
                        if score > best_score:
                            best_score = score
                            best_match = columns[i]
                    elif col in pattern:
                        score = len(col)  # Column name is part of pattern
                        if score > best_score:
                            best_score = score
                            best_match = columns[i]
            
            if best_match:
                mapping[field] = best_match
        
        self.logger.info("Column mapping result", mapping=mapping)
        
        # If we couldn't find a date column, try more flexible matching
        if not mapping.get('date'):
            for i, col in enumerate(normalized_columns):
                if any(char.isdigit() for char in col) and ('date' in col or 'dt' in col or col.startswith('d')):
                    mapping['date'] = columns[i]
                    break
            
            # Even more flexible - any column that might contain dates
            if not mapping.get('date'):
                for i, col in enumerate(columns):
                    if any(word in col.lower() for word in ['date', 'time', 'dt', 'day']):
                        mapping['date'] = col
                        break
        
        return mapping
    
    def _extract_amount_and_type(self, row: Dict[str, Any], column_mapping: Dict[str, str]) -> Tuple[float, str]:
        """Extract amount and transaction type from row"""
        
        # Check for separate debit/credit columns
        debit_col = column_mapping.get('debit')
        credit_col = column_mapping.get('credit')
        amount_col = column_mapping.get('amount')
        
        if debit_col and credit_col:
            # Separate debit/credit columns
            debit_value = row.get(debit_col, 0)
            credit_value = row.get(credit_col, 0)
            
            debit_amount = self._parse_amount(str(debit_value)) if debit_value else 0
            credit_amount = self._parse_amount(str(credit_value)) if credit_value else 0
            
            if debit_amount > 0:
                return debit_amount, 'debit'
            elif credit_amount > 0:
                return credit_amount, 'credit'
            else:
                return 0, 'debit'
                
        elif amount_col:
            # Single amount column
            amount_value = row.get(amount_col, 0)
            amount = self._parse_amount(str(amount_value))
            
            # Determine type based on sign or other indicators
            if amount < 0:
                return abs(amount), 'debit'
            else:
                return amount, 'credit'
        
        else:
            # Try to find any numeric column
            for key, value in row.items():
                if value:
                    amount = self._parse_amount(str(value))
                    if amount > 0:
                        return amount, 'debit'  # Default to debit
        
        return 0, 'debit'
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string using various formats"""
        if not date_str or date_str.strip() == '':
            return None
        
        date_str = date_str.strip()
        
        # Remove common prefixes/suffixes
        date_str = re.sub(r'[^\d/\-\.\s\w]', '', date_str)
        
        for date_format in self.date_formats:
            try:
                parsed_date = datetime.strptime(date_str, date_format).date()
                return parsed_date
            except ValueError:
                continue
        
        # Try pandas date parser as last resort
        try:
            import pandas as pd
            parsed_date = pd.to_datetime(date_str, dayfirst=True).date()
            return parsed_date
        except Exception:
            pass
        
        return None
    
    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount string to float"""
        if not amount_str or str(amount_str).strip() == '':
            return 0.0
        
        # Clean the amount string
        amount_str = str(amount_str).strip()
        
        # Remove currency symbols and commas
        amount_str = re.sub(r'[₹$€£,\s]', '', amount_str)
        
        # Handle negative amounts
        is_negative = False
        if amount_str.startswith('-') or amount_str.startswith('('):
            is_negative = True
            amount_str = amount_str.replace('-', '').replace('(', '').replace(')', '')
        
        # Extract numeric value
        numeric_match = re.search(r'\d+\.?\d*', amount_str)
        if not numeric_match:
            return 0.0
        
        try:
            amount = float(numeric_match.group())
            return -amount if is_negative else amount
        except ValueError:
            return 0.0
    
    def validate_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Validate uploaded file
        
        Args:
            file_content: File content
            filename: Original filename
            
        Returns:
            Validation result
        """
        try:
            file_ext = Path(filename).suffix.lower()
            file_size = len(file_content)
            
            # Check file type
            if file_ext not in ['.csv', '.xlsx', '.xls', '.pdf']:
                return {
                    "valid": False,
                    "errors": [f"Unsupported file type: {file_ext}"],
                    "file_type": file_ext,
                    "file_size": file_size
                }
            
            # Check file size
            if file_size > self.settings.max_file_size_bytes:
                return {
                    "valid": False,
                    "errors": [f"File too large. Maximum size: {self.settings.max_file_size_mb}MB"],
                    "file_type": file_ext,
                    "file_size": file_size
                }
            
            # Check if file is empty
            if file_size == 0:
                return {
                    "valid": False,
                    "errors": ["File is empty"],
                    "file_type": file_ext,
                    "file_size": file_size
                }
            
            return {
                "valid": True,
                "file_type": file_ext,
                "file_size": file_size,
                "errors": [],
                "warnings": []
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"File validation error: {str(e)}"],
                "file_type": "unknown",
                "file_size": len(file_content) if file_content else 0
            }