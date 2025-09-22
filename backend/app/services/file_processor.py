"""
Enhanced file processing service for handling CSV, Excel, and PDF files
with improved bank statement transaction extraction
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
    Enhanced version with improved PDF parsing logic for Indian bank statements.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = logger.bind(service="FileProcessor")
        
        # Enhanced column mapping patterns for Indian banks
        self.column_mappings = {
            'date': ['date', 'txn date', 'transaction date', 'value date', 'posted date', 'txn_date', 'dt'],
            'description': ['description', 'narration', 'particulars', 'transaction details', 'remarks', 'reference', 'details'],
            'debit': ['debit', 'debit amount', 'withdrawal', 'dr', 'debit_amount', 'withdrawals'],
            'credit': ['credit', 'credit amount', 'deposit', 'cr', 'credit_amount', 'deposits'],
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
        Enhanced to handle B/F entries with null amounts
        """
        try:
            if not parsed_date:
                self.logger.debug("Skipping transaction: no valid date")
                return None
                
            if not description or str(description).strip() == '':
                description = "Transaction"
            else:
                description = str(description).strip()
                
            # Allow amount to be None for B/F entries and similar
            if amount is not None and amount <= 0:
                self.logger.debug("Skipping transaction: invalid amount", amount=amount)
                return None
                
            if txn_type and txn_type not in ['debit', 'credit']:
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
                amount=float(amount) if amount is not None else None,
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
        """Enhanced PDF processing entry point"""
        try:
            self.logger.info("Processing PDF file")
            
            # Try with enhanced pdfplumber first
            try:
                transactions = await self._process_pdf_with_pdfplumber(file_content)
                if transactions:
                    return transactions
            except Exception as e:
                self.logger.warning("Enhanced pdfplumber processing failed", error=str(e))
            
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
        """
        Enhanced PDF processing with improved table extraction logic
        """
        transactions = []
        
        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                self.logger.info(f"Processing PDF with {len(pdf.pages)} pages")
                
                for page_num, page in enumerate(pdf.pages):
                    self.logger.debug(f"Processing page {page_num + 1}")
                    
                    # Extract tables with enhanced settings
                    tables = page.extract_tables(table_settings={
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                        "min_words_vertical": 3,
                        "min_words_horizontal": 1
                    })
                    
                    page_transactions = []
                    
                    if tables:
                        self.logger.debug(f"Found {len(tables)} tables on page {page_num + 1}")
                        
                        for table_num, table in enumerate(tables):
                            if not table or len(table) < 2:
                                continue
                            
                            try:
                                # Enhanced table processing
                                table_transactions = self._extract_transactions_from_table(table)
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
                                text_transactions = self._extract_transactions_from_text_enhanced(text)
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

    def _extract_transactions_from_table(self, table: List[List[str]]) -> List[Transaction]:
        """
        Enhanced table processing with intelligent column detection
        """
        transactions = []
        
        if not table or len(table) < 2:
            return transactions
        
        # Find header row and identify column structure
        header_info = self._analyze_table_structure(table)
        
        if not header_info:
            self.logger.warning("Could not analyze table structure")
            return transactions
        
        header_row_idx = header_info['header_row_idx']
        column_mapping = header_info['column_mapping']
        
        self.logger.debug(f"Table structure: header at row {header_row_idx}, mapping: {column_mapping}")
        
        # Process data rows
        for row_idx in range(header_row_idx + 1, len(table)):
            row = table[row_idx]
            
            if not row or len(row) < 2:
                continue
                
            # Skip empty rows
            if not any(cell and str(cell).strip() for cell in row):
                continue
            
            try:
                transaction = self._parse_table_row(row, column_mapping)
                if transaction:
                    transactions.append(transaction)
                    
            except Exception as e:
                self.logger.debug(f"Failed to parse table row {row_idx}: {str(e)}")
                continue
        
        return transactions

    def _analyze_table_structure(self, table: List[List[str]]) -> Optional[Dict]:
        """
        Analyze table structure to identify columns and header position
        """
        header_candidates = []
        
        # Look for header row in first few rows
        for i, row in enumerate(table[:3]):
            if not row:
                continue
                
            row_text = ' '.join(str(cell).lower() if cell else '' for cell in row)
            header_score = 0
            
            # Score based on presence of header keywords
            header_keywords = ['date', 'description', 'particulars', 'debit', 'credit', 
                             'withdrawal', 'deposit', 'balance', 'deposits', 'withdrawals']
            for keyword in header_keywords:
                if keyword in row_text:
                    header_score += 1
            
            header_candidates.append({
                'row_idx': i,
                'row': row,
                'score': header_score
            })
        
        # Select best header candidate
        if not header_candidates:
            return None
            
        best_header = max(header_candidates, key=lambda x: x['score'])
        
        if best_header['score'] == 0:
            # No clear header found, assume first row is header
            best_header = {'row_idx': 0, 'row': table[0] if table else [], 'score': 0}
        
        if not best_header['row']:
            return None
        
        # Map columns
        header_row = best_header['row']
        column_mapping = self._map_table_columns(header_row)
        
        return {
            'header_row_idx': best_header['row_idx'],
            'column_mapping': column_mapping,
            'num_columns': len(header_row)
        }

    def _map_table_columns(self, header_row: List[str]) -> Dict[str, int]:
        """
        Map table columns to field types based on header content
        """
        column_mapping = {}
        
        for i, header in enumerate(header_row):
            if not header:
                continue
                
            header_lower = str(header).lower().strip()
            
            # Map to field types with priority order
            if any(keyword in header_lower for keyword in ['date', 'dt']) and 'date' not in column_mapping:
                column_mapping['date'] = i
            elif any(keyword in header_lower for keyword in ['description', 'particulars', 'narration', 'details']) and 'description' not in column_mapping:
                column_mapping['description'] = i
            elif any(keyword in header_lower for keyword in ['withdrawal', 'debit', 'dr']) and 'debit' not in column_mapping:
                column_mapping['debit'] = i
            elif any(keyword in header_lower for keyword in ['deposit', 'credit', 'cr']) and 'credit' not in column_mapping:
                column_mapping['credit'] = i
            elif any(keyword in header_lower for keyword in ['balance']) and 'balance' not in column_mapping:
                column_mapping['balance'] = i
            elif any(keyword in header_lower for keyword in ['amount']) and 'amount' not in column_mapping:
                column_mapping['amount'] = i
        
        # If no explicit debit/credit columns found, try to infer structure
        if 'debit' not in column_mapping and 'credit' not in column_mapping and 'amount' not in column_mapping:
            # Look for numeric columns that could be amounts
            for i, header in enumerate(header_row):
                if header and i > 1:  # Skip date and description columns
                    if 'balance' not in column_mapping or i != column_mapping['balance']:
                        if 'amount' not in column_mapping:
                            column_mapping['amount'] = i
                            break
        
        self.logger.debug("Table column mapping", mapping=column_mapping, headers=header_row)
        return column_mapping

    def _parse_table_row(self, row: List[str], column_mapping: Dict[str, int]) -> Optional[Transaction]:
        """
        Parse individual table row into transaction with enhanced logic
        """
        try:
            # Extract date
            date_idx = column_mapping.get('date', 0)
            if date_idx >= len(row):
                return None
                
            date_str = str(row[date_idx]).strip() if row[date_idx] else ""
            parsed_date = self._parse_date(date_str)
            
            if not parsed_date:
                return None
            
            # Extract description
            desc_idx = column_mapping.get('description', 1)
            description = ""
            if desc_idx < len(row) and row[desc_idx]:
                description = str(row[desc_idx]).strip()
                # Clean up description - remove extra whitespace and artifacts
                description = re.sub(r'\s+', ' ', description)
            
            # Enhanced amount and type extraction
            amount, txn_type, balance = self._extract_amount_type_balance_from_row(row, column_mapping)
            
            # Special handling for B/F (brought forward) entries
            if description.upper().startswith('B/F') or 'B/F' in description.upper():
                if amount == 0 or amount is None:
                    amount = None  # B/F entries don't have transaction amounts
                    txn_type = None
            
            # Skip if we couldn't extract meaningful data (except for B/F entries)
            if not description and amount == 0:
                return None
            
            if not description:
                description = "Transaction"
            
            # Create transaction
            return self._create_transaction_safely(
                parsed_date=parsed_date,
                description=description,
                amount=amount,
                txn_type=txn_type,
                balance=balance
            )
            
        except Exception as e:
            self.logger.debug("Failed to parse table row", error=str(e))
            return None

    def _extract_amount_type_balance_from_row(self, row: List[str], column_mapping: Dict[str, int]) -> Tuple[Optional[float], Optional[str], Optional[float]]:
        """
        Enhanced extraction of amount, transaction type, and balance from row
        """
        debit_idx = column_mapping.get('debit')
        credit_idx = column_mapping.get('credit')
        amount_idx = column_mapping.get('amount')
        balance_idx = column_mapping.get('balance')
        
        amount = None
        txn_type = None
        balance = None
        
        # Extract balance first (usually the last numeric column)
        if balance_idx is not None and balance_idx < len(row):
            balance_val = self._parse_amount(str(row[balance_idx])) if row[balance_idx] else 0
            balance = balance_val if balance_val > 0 else None
        else:
            # Try to find balance as the last numeric column
            for i in range(len(row) - 1, -1, -1):
                if row[i]:
                    potential_balance = self._parse_amount(str(row[i]))
                    if potential_balance > 0:
                        balance = potential_balance
                        balance_idx = i  # Remember for later exclusion
                        break
        
        # Extract amount and type based on column structure
        if debit_idx is not None and credit_idx is not None:
            # Separate debit/credit columns (ICICI format)
            debit_amount = 0
            credit_amount = 0
            
            if debit_idx < len(row) and row[debit_idx]:
                debit_amount = self._parse_amount(str(row[debit_idx]))
            
            if credit_idx < len(row) and row[credit_idx]:
                credit_amount = self._parse_amount(str(row[credit_idx]))
            
            if debit_amount > 0:
                amount = debit_amount
                txn_type = 'debit'
            elif credit_amount > 0:
                amount = credit_amount
                txn_type = 'credit'
            else:
                amount = 0
                txn_type = 'debit'
                
        elif amount_idx is not None:
            # Single amount column
            if amount_idx < len(row) and row[amount_idx]:
                amount_val = self._parse_amount(str(row[amount_idx]))
                if amount_val != 0:
                    amount = abs(amount_val)
                    # Determine type from sign or context
                    if amount_val < 0:
                        txn_type = 'debit'
                    else:
                        # Use description to determine type
                        desc_idx = column_mapping.get('description', 1)
                        description = str(row[desc_idx]).lower() if desc_idx < len(row) and row[desc_idx] else ""
                        if any(word in description for word in ['deposit', 'credit', 'salary', 'transfer in', 'cms']):
                            txn_type = 'credit'
                        else:
                            txn_type = 'debit'
                else:
                    amount = 0
                    txn_type = 'debit'
        else:
            # No explicit amount column - try to find numeric values
            numeric_values = []
            for i, cell in enumerate(row):
                if cell and i != balance_idx:  # Exclude balance column
                    parsed_val = self._parse_amount(str(cell))
                    if parsed_val > 0:
                        numeric_values.append((i, parsed_val))
            
            # Remove the balance value if it appeared in the numeric values
            if balance and numeric_values:
                numeric_values = [(i, val) for i, val in numeric_values if abs(val - balance) > 0.01]
            
            if numeric_values:
                # Take the first non-balance numeric value as amount
                amount = numeric_values[0][1]
                # Determine type from description
                desc_idx = column_mapping.get('description', 1)
                description = str(row[desc_idx]).lower() if desc_idx < len(row) and row[desc_idx] else ""
                if any(word in description for word in ['deposit', 'credit', 'salary', 'cms', 'transfer in']):
                    txn_type = 'credit'
                else:
                    txn_type = 'debit'
            else:
                amount = 0
                txn_type = 'debit'
        
        # Special case: If amount is 0 but we have a balance, check for B/F entry
        if (amount == 0 or amount is None) and balance and balance > 0:
            desc_idx = column_mapping.get('description', 1)
            description = str(row[desc_idx]).upper() if desc_idx < len(row) and row[desc_idx] else ""
            if 'B/F' in description or 'BROUGHT FORWARD' in description:
                return None, None, balance  # B/F entries have no amount, just balance
        
        return amount if amount and amount > 0 else None, txn_type, balance

    def _extract_transactions_from_text_enhanced(self, text: str) -> List[Transaction]:
        """
        Enhanced text extraction with multi-line transaction support for ICICI bank statements
        """
        transactions = []
        
        # Pre-process text to handle multi-line transactions
        processed_text = self._preprocess_multiline_transactions(text)
        
        # Enhanced patterns for ICICI bank statements
        patterns = [
            # Pattern 1: ICICI format - Date Description Deposits Withdrawals Balance
            r'(\d{1,2}-\d{1,2}-\d{4})\s+(.+?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            # Pattern 2: B/F entry - Date B/F Balance
            r'(\d{1,2}-\d{1,2}-\d{4})\s+(B/F)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            # Pattern 3: Single amount column format
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+(.{10,}?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        ]
        
        lines = processed_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            # Skip header lines, page markers, and totals
            if any(header in line.upper() for header in ['DATE', 'MODE', 'PARTICULARS', 'WITHDRAWALS', 'DEPOSITS', 'BALANCE', 'PAGE', 'STATEMENT', 'TOTAL:']):
                continue
            
            # Try each pattern
            for pattern_idx, pattern in enumerate(patterns):
                match = re.search(pattern, line)
                if match:
                    try:
                        groups = match.groups()
                        
                        if len(groups) >= 3:
                            date_str = groups[0]
                            
                            # Parse date
                            parsed_date = self._parse_date(date_str)
                            if not parsed_date:
                                continue
                            
                            # Handle different patterns
                            if len(groups) == 3 and groups[1].upper().strip() == 'B/F':
                                # B/F entry
                                description = "B/F"
                                amount = None
                                txn_type = None
                                balance = self._parse_amount(groups[2])
                            elif len(groups) == 5:
                                # Full format with deposits/withdrawals
                                description = groups[1].strip()
                                deposits = self._parse_amount(groups[2])
                                withdrawals = self._parse_amount(groups[3])
                                balance = self._parse_amount(groups[4])
                                
                                if deposits > 0:
                                    amount = deposits
                                    txn_type = 'credit'
                                elif withdrawals > 0:
                                    amount = withdrawals
                                    txn_type = 'debit'
                                else:
                                    continue
                            else:
                                # Amount and balance format
                                description = groups[1].strip()
                                amount = self._parse_amount(groups[2])
                                balance = self._parse_amount(groups[3])
                                
                                # Determine transaction type
                                desc_upper = description.upper()
                                if any(word in desc_upper for word in ['CMS', 'DEPOSIT', 'CREDIT', 'SALARY', 'TRANSFER IN']):
                                    txn_type = 'credit'
                                else:
                                    txn_type = 'debit'
                            
                            # Clean description
                            if description and len(description) > 3:
                                description = re.sub(r'\s+', ' ', description)
                            else:
                                description = "Transaction"
                            
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
                                self.logger.debug(f"Extracted transaction: {date_str} - {description[:30]}...")
                            break
                            
                    except Exception as e:
                        self.logger.debug("Failed to parse transaction from enhanced text", 
                                        line=line[:100], error=str(e))
                        continue
        
        self.logger.info(f"Enhanced text extraction found {len(transactions)} transactions")
        
        # If we found fewer transactions than expected, try alternative extraction
        if len(transactions) < 50:  # Expected around 59 transactions
            self.logger.warning("Found fewer transactions than expected, trying alternative extraction")
            alternative_transactions = self._extract_transactions_alternative_method(text)
            if len(alternative_transactions) > len(transactions):
                self.logger.info(f"Alternative method found {len(alternative_transactions)} transactions, using those")
                return alternative_transactions
        
        return transactions

    def _preprocess_multiline_transactions(self, text: str) -> str:
        """
        Preprocess text to combine multi-line transactions into single lines
        """
        lines = text.split('\n')
        processed_lines = []
        current_transaction = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_transaction:
                    processed_lines.append(' '.join(current_transaction))
                    current_transaction = []
                continue
            
            # Check if this line starts a new transaction (has a date)
            if re.match(r'^\d{1,2}-\d{1,2}-\d{4}', line):
                # Save previous transaction if exists
                if current_transaction:
                    processed_lines.append(' '.join(current_transaction))
                current_transaction = [line]
            elif current_transaction:
                # This is a continuation line
                current_transaction.append(line)
            else:
                # Standalone line (headers, etc.)
                processed_lines.append(line)
        
        # Don't forget the last transaction
        if current_transaction:
            processed_lines.append(' '.join(current_transaction))
        
        return '\n'.join(processed_lines)

    def _extract_transactions_alternative_method(self, text: str) -> List[Transaction]:
        """
        Alternative extraction method using more flexible parsing
        """
        transactions = []
        
        # Split text into potential transaction blocks
        # Look for date patterns and collect everything until the next date or end
        date_pattern = r'(\d{1,2}-\d{1,2}-\d{4})'
        
        # Find all date positions
        import re
        date_matches = list(re.finditer(date_pattern, text))
        
        for i, match in enumerate(date_matches):
            try:
                start_pos = match.start()
                end_pos = date_matches[i + 1].start() if i + 1 < len(date_matches) else len(text)
                
                transaction_block = text[start_pos:end_pos].strip()
                
                # Extract transaction from this block
                transaction = self._parse_transaction_block(transaction_block)
                if transaction:
                    transactions.append(transaction)
                    
            except Exception as e:
                self.logger.debug(f"Failed to parse transaction block: {str(e)}")
                continue
        
        return transactions

    def _parse_transaction_block(self, block: str) -> Optional[Transaction]:
        """
        Parse a transaction block that may span multiple lines
        """
        try:
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            if not lines:
                return None
            
            first_line = lines[0]
            
            # Extract date
            date_match = re.match(r'^(\d{1,2}-\d{1,2}-\d{4})', first_line)
            if not date_match:
                return None
            
            date_str = date_match.group(1)
            parsed_date = self._parse_date(date_str)
            if not parsed_date:
                return None
            
            # Combine all lines after date to form the full transaction text
            full_text = first_line[len(date_str):].strip()
            for line in lines[1:]:
                full_text += " " + line
            
            # Clean up the text
            full_text = re.sub(r'\s+', ' ', full_text).strip()
            
            # Handle B/F entries
            if full_text.upper().startswith('B/F'):
                balance_match = re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', full_text)
                if balance_match:
                    balance = self._parse_amount(balance_match.group(1))
                    return self._create_transaction_safely(
                        parsed_date=parsed_date,
                        description="B/F",
                        amount=None,
                        txn_type=None,
                        balance=balance
                    )
                return None
            
            # Extract numeric values (amounts and balance)
            numeric_values = []
            for match in re.finditer(r'\b(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b', full_text):
                value = self._parse_amount(match.group(1))
                if value > 0:
                    numeric_values.append(value)
            
            if len(numeric_values) < 2:
                return None
            
            # The balance is typically the last (largest) number
            balance = max(numeric_values) if numeric_values else None
            
            # Remove balance from consideration for amount
            if balance in numeric_values:
                numeric_values.remove(balance)
            
            # The amount should be the remaining number(s)
            amount = numeric_values[0] if numeric_values else 0
            
            # Extract description (everything before the numeric values)
            description = full_text
            for match in re.finditer(r'\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b', full_text):
                description = description.replace(match.group(0), '', 1)
            
            description = description.strip()
            if len(description) < 3:
                description = "Transaction"
            
            # Determine transaction type
            desc_upper = description.upper()
            if any(word in desc_upper for word in ['CMS', 'DEPOSIT', 'CREDIT', 'SALARY']):
                txn_type = 'credit'
            else:
                txn_type = 'debit'
            
            return self._create_transaction_safely(
                parsed_date=parsed_date,
                description=description,
                amount=amount if amount > 0 else None,
                txn_type=txn_type,
                balance=balance
            )
            
        except Exception as e:
            self.logger.debug(f"Failed to parse transaction block: {str(e)}")
            return None

    async def _process_pdf_with_pypdf2(self, file_content: bytes) -> List[Transaction]:
        """Process PDF using PyPDF2 as fallback"""
        transactions = []
        
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            
            for page_num, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text:
                    try:
                        page_transactions = self._extract_transactions_from_text_enhanced(text)
                        transactions.extend(page_transactions)
                        self.logger.debug(f"PyPDF2 - Page {page_num + 1}: extracted {len(page_transactions)} transactions")
                    except Exception as e:
                        self.logger.warning(f"Failed to extract from PDF page {page_num + 1}: {str(e)}")
                        continue
        except Exception as e:
            self.logger.error(f"Error processing PDF with PyPDF2: {str(e)}")
            raise
        
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
        """Enhanced date parsing with better format support"""
        if not date_str or date_str.strip() == '':
            return None
        
        date_str = date_str.strip()
        
        # Remove common prefixes/suffixes and clean up
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
        """Enhanced amount parsing with better number recognition"""
        if not amount_str or str(amount_str).strip() == '':
            return 0.0
        
        # Clean the amount string
        amount_str = str(amount_str).strip()
        
        # Remove currency symbols and commas
        amount_str = re.sub(r'[₹$€£,\s]', '', amount_str)
        
        # Handle negative amounts and parentheses
        is_negative = False
        if amount_str.startswith('-') or amount_str.startswith('(') or amount_str.endswith(')'):
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

    async def _process_pdf_with_pypdf2(self, file_content: bytes) -> List[Transaction]:
        """Process PDF using PyPDF2 as fallback"""
        transactions = []
        
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            
            for page_num, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text:
                    try:
                        page_transactions = self._extract_transactions_from_text_enhanced(text)
                        transactions.extend(page_transactions)
                        self.logger.debug(f"PyPDF2 - Page {page_num + 1}: extracted {len(page_transactions)} transactions")
                    except Exception as e:
                        self.logger.warning(f"Failed to extract from PDF page {page_num + 1}: {str(e)}")
                        continue
        except Exception as e:
            self.logger.error(f"Error processing PDF with PyPDF2: {str(e)}")
            raise
        
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
        """Enhanced date parsing with better format support"""
        if not date_str or date_str.strip() == '':
            return None
        
        date_str = date_str.strip()
        
        # Remove common prefixes/suffixes and clean up
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
        """Enhanced amount parsing with better number recognition"""
        if not amount_str or str(amount_str).strip() == '':
            return 0.0
        
        # Clean the amount string
        amount_str = str(amount_str).strip()
        
        # Remove currency symbols and commas
        amount_str = re.sub(r'[₹$€£,\s]', '', amount_str)
        
        # Handle negative amounts and parentheses
        is_negative = False
        if amount_str.startswith('-') or amount_str.startswith('(') or amount_str.endswith(')'):
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