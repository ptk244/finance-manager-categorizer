import os
from datetime import datetime
from typing import Any, Dict, List

from agno.agent import Agent
from agno.tools.file import FileTools
from loguru import logger

from models.transaction import (ProcessedBankStatement, Transaction,
                                TransactionType)
from tools.file_extraction_tools import file_extraction_tools


class FileProcessorAgent:
    """Agent responsible for processing uploaded files and extracting transaction data"""
    
    def __init__(self):
        self.agent = Agent(
            name="FileProcessorAgent",
            description="Specialized in extracting and processing financial transaction data from various file formats (CSV, Excel, PDF)",
            instructions=[
                "You are a financial data extraction specialist.",
                "Your primary job is to extract transaction data from uploaded bank statements.",
                "You can handle CSV, Excel, and PDF files.",
                "Always validate the extracted data for completeness and accuracy.",
                "Identify transaction dates, descriptions, amounts, and types (debit/credit).",
                "Calculate running balances when possible.",
                "Handle Indian currency formats and date formats.",
                "Provide detailed extraction reports with statistics."
            ],
            tools=[
                FileTools(),  # Agno's built-in file tools
                file_extraction_tools  # Our custom extraction tools
            ],
            # show_tool_calls=True,
            debug_mode=True
        )
    
    async def process_uploaded_file(self, file_path: str, file_name: str) -> Dict[str, Any]:
        """Process an uploaded file and extract transaction data"""
        try:
            logger.info(f"Starting file processing for: {file_name}")
            
            # Determine file type and use appropriate extraction method
            file_extension = os.path.splitext(file_name)[1].lower()
            
            if file_extension == '.csv':
                extraction_result = file_extraction_tools.extract_csv_data(file_path)
            elif file_extension in ['.xlsx', '.xls']:
                extraction_result = file_extraction_tools.extract_excel_data(file_path)
            elif file_extension == '.pdf':
                extraction_result = file_extraction_tools.extract_pdf_data(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
            
            if not extraction_result.get('success', False):
                raise Exception(f"Extraction failed: {extraction_result.get('error', 'Unknown error')}")
            
            transactions_data = extraction_result['transactions']
            
            # Convert to Transaction objects and validate
            processed_transactions = []
            total_debits = 0
            total_credits = 0
            date_range = {'start': None, 'end': None}
            
            for trans_data in transactions_data:
                try:
                    # Parse transaction
                    transaction_date = datetime.fromisoformat(trans_data['date'])
                    
                    # Update date range
                    if date_range['start'] is None or transaction_date < date_range['start']:
                        date_range['start'] = transaction_date
                    if date_range['end'] is None or transaction_date > date_range['end']:
                        date_range['end'] = transaction_date
                    
                    # Create transaction object
                    transaction = Transaction(
                        date=transaction_date,
                        description=trans_data['description'],
                        amount=abs(trans_data['amount']),
                        transaction_type=TransactionType(trans_data['transaction_type']),
                        balance=trans_data.get('balance')
                    )
                    
                    processed_transactions.append(transaction)
                    
                    # Update totals
                    if transaction.transaction_type == TransactionType.DEBIT:
                        total_debits += transaction.amount
                    else:
                        total_credits += transaction.amount
                        
                except Exception as e:
                    logger.warning(f"Skipping invalid transaction: {str(e)}")
                    continue
            
            if not processed_transactions:
                raise Exception("No valid transactions found in file")
            
            # Create processed statement
            processed_statement = ProcessedBankStatement(
                file_name=file_name,
                total_transactions=len(processed_transactions),
                date_range=date_range,
                total_debits=total_debits,
                total_credits=total_credits,
                current_balance=processed_transactions[-1].balance if processed_transactions[-1].balance else None,
                transactions=processed_transactions
            )
            
            logger.info(f"Successfully processed {len(processed_transactions)} transactions")
            
            return {
                'success': True,
                'processed_statement': processed_statement,
                'extraction_stats': {
                    'raw_transactions': len(transactions_data),
                    'valid_transactions': len(processed_transactions),
                    'success_rate': len(processed_transactions) / len(transactions_data) * 100,
                    'date_range_days': (date_range['end'] - date_range['start']).days if date_range['start'] and date_range['end'] else 0,
                    'total_debits': total_debits,
                    'total_credits': total_credits,
                    'net_amount': total_credits - total_debits
                }
            }
            
        except Exception as e:
            logger.error(f"File processing failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'processed_statement': None
            }
    
    async def validate_extracted_data(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate extracted transaction data for completeness and accuracy"""
        try:
            validation_results = {
                'total_transactions': len(transactions),
                'valid_transactions': 0,
                'invalid_transactions': 0,
                'issues': [],
                'warnings': []
            }
            
            for i, transaction in enumerate(transactions):
                issues = []
                
                # Check required fields
                if not transaction.get('date'):
                    issues.append(f"Missing date in transaction {i+1}")
                if not transaction.get('description'):
                    issues.append(f"Missing description in transaction {i+1}")
                if not transaction.get('amount') or transaction.get('amount') <= 0:
                    issues.append(f"Invalid amount in transaction {i+1}")
                if transaction.get('transaction_type') not in ['debit', 'credit']:
                    issues.append(f"Invalid transaction type in transaction {i+1}")
                
                # Check data quality
                if transaction.get('description') and len(transaction['description'].strip()) < 3:
                    validation_results['warnings'].append(f"Very short description in transaction {i+1}")
                
                if issues:
                    validation_results['invalid_transactions'] += 1
                    validation_results['issues'].extend(issues)
                else:
                    validation_results['valid_transactions'] += 1
            
            validation_results['validation_success'] = validation_results['invalid_transactions'] == 0
            validation_results['data_quality_score'] = (validation_results['valid_transactions'] / 
                                                       validation_results['total_transactions']) * 100
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Data validation failed: {str(e)}")
            return {
                'validation_success': False,
                'error': str(e)
            }
    
    async def get_file_metadata(self, file_path: str, file_name: str) -> Dict[str, Any]:
        """Extract metadata from the uploaded file"""
        try:
            file_stats = os.stat(file_path)
            file_extension = os.path.splitext(file_name)[1].lower()
            
            metadata = {
                'file_name': file_name,
                'file_size': file_stats.st_size,
                'file_extension': file_extension,
                'upload_time': datetime.now().isoformat(),
                'file_type': self._get_file_type_description(file_extension)
            }
            
            # Try to get additional format-specific metadata
            if file_extension == '.csv':
                try:
                    import pandas as pd
                    df = pd.read_csv(file_path, nrows=0)  # Just headers
                    metadata['columns'] = list(df.columns)
                    metadata['column_count'] = len(df.columns)
                except:
                    pass
            elif file_extension in ['.xlsx', '.xls']:
                try:
                    import pandas as pd
                    xl_file = pd.ExcelFile(file_path)
                    metadata['sheet_names'] = xl_file.sheet_names
                    metadata['sheet_count'] = len(xl_file.sheet_names)
                except:
                    pass
            
            return metadata
            
        except Exception as e:
            logger.error(f"Metadata extraction failed: {str(e)}")
            return {
                'file_name': file_name,
                'error': str(e)
            }
    
    def _get_file_type_description(self, extension: str) -> str:
        """Get human-readable file type description"""
        type_map = {
            '.csv': 'Comma-Separated Values',
            '.xlsx': 'Excel Workbook',
            '.xls': 'Excel Legacy Format',
            '.pdf': 'Portable Document Format'
        }
        return type_map.get(extension, 'Unknown Format')

# Create agent instance
file_processor_agent = FileProcessorAgent()