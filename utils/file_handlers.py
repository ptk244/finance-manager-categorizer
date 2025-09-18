"""
File handling utilities for Finance Manager Categorizer

This module provides comprehensive file handling capabilities for various
formats commonly used in financial data processing.
"""

import hashlib
import mimetypes
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Union

import pandas as pd
import pdfplumber
import PyPDF2
from loguru import logger
from openpyxl import load_workbook


class FileHandler:
    """Comprehensive file handling utilities"""
    
    SUPPORTED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.pdf'}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize FileHandler
        
        Args:
            temp_dir: Optional temporary directory for file operations
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        
    def validate_file(self, file_path: str, max_size: Optional[int] = None) -> Dict[str, Any]:
        """
        Validate uploaded file for processing
        
        Args:
            file_path: Path to the file to validate
            max_size: Maximum allowed file size in bytes
            
        Returns:
            Dict containing validation results
        """
        try:
            if not os.path.exists(file_path):
                return {
                    'valid': False,
                    'error': 'File does not exist',
                    'error_code': 'FILE_NOT_FOUND'
                }
            
            # Check file size
            file_size = os.path.getsize(file_path)
            max_allowed = max_size or self.MAX_FILE_SIZE
            
            if file_size > max_allowed:
                return {
                    'valid': False,
                    'error': f'File too large: {file_size} bytes (max: {max_allowed})',
                    'error_code': 'FILE_TOO_LARGE',
                    'file_size': file_size,
                    'max_size': max_allowed
                }
            
            # Check file extension
            file_extension = Path(file_path).suffix.lower()
            if file_extension not in self.SUPPORTED_EXTENSIONS:
                return {
                    'valid': False,
                    'error': f'Unsupported file type: {file_extension}',
                    'error_code': 'UNSUPPORTED_FORMAT',
                    'supported_formats': list(self.SUPPORTED_EXTENSIONS)
                }
            
            # Check if file is readable
            try:
                with open(file_path, 'rb') as f:
                    f.read(1024)  # Try to read first 1KB
            except Exception as e:
                return {
                    'valid': False,
                    'error': f'File is not readable: {str(e)}',
                    'error_code': 'FILE_NOT_READABLE'
                }
            
            # Detect MIME type
            mime_type, encoding = mimetypes.guess_type(file_path)
            
            return {
                'valid': True,
                'file_size': file_size,
                'file_extension': file_extension,
                'mime_type': mime_type,
                'encoding': encoding,
                'readable': True
            }
            
        except Exception as e:
            logger.error(f"File validation failed: {str(e)}")
            return {
                'valid': False,
                'error': f'Validation failed: {str(e)}',
                'error_code': 'VALIDATION_ERROR'
            }
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get comprehensive file information
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dict containing file information
        """
        try:
            if not os.path.exists(file_path):
                return {'error': 'File does not exist'}
            
            stat_info = os.stat(file_path)
            file_path_obj = Path(file_path)
            
            # Calculate file hash for integrity checking
            file_hash = self._calculate_file_hash(file_path)
            
            return {
                'filename': file_path_obj.name,
                'stem': file_path_obj.stem,
                'suffix': file_path_obj.suffix,
                'size': stat_info.st_size,
                'size_human': self._format_file_size(stat_info.st_size),
                'created_time': datetime.fromtimestamp(stat_info.st_ctime),
                'modified_time': datetime.fromtimestamp(stat_info.st_mtime),
                'accessed_time': datetime.fromtimestamp(stat_info.st_atime),
                'permissions': oct(stat_info.st_mode)[-3:],
                'is_readable': os.access(file_path, os.R_OK),
                'is_writable': os.access(file_path, os.W_OK),
                'absolute_path': file_path_obj.absolute(),
                'file_hash': file_hash,
                'mime_type': mimetypes.guess_type(file_path)[0]
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info: {str(e)}")
            return {'error': str(e)}
    
    def create_temp_file(self, suffix: str = '', prefix: str = 'finmgr_') -> str:
        """
        Create a temporary file for processing
        
        Args:
            suffix: File suffix/extension
            prefix: File prefix
            
        Returns:
            Path to created temporary file
        """
        try:
            temp_file = tempfile.NamedTemporaryFile(
                suffix=suffix,
                prefix=prefix,
                dir=self.temp_dir,
                delete=False
            )
            temp_file.close()
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Failed to create temp file: {str(e)}")
            raise
    
    def copy_file(self, source: str, destination: str, overwrite: bool = False) -> Dict[str, Any]:
        """
        Copy file with validation and error handling
        
        Args:
            source: Source file path
            destination: Destination file path
            overwrite: Whether to overwrite existing destination
            
        Returns:
            Dict with copy operation results
        """
        try:
            if not os.path.exists(source):
                return {
                    'success': False,
                    'error': 'Source file does not exist'
                }
            
            if os.path.exists(destination) and not overwrite:
                return {
                    'success': False,
                    'error': 'Destination file already exists'
                }
            
            # Create destination directory if it doesn't exist
            dest_dir = Path(destination).parent
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Perform copy
            shutil.copy2(source, destination)
            
            # Verify copy
            if not os.path.exists(destination):
                return {
                    'success': False,
                    'error': 'Copy operation failed - destination file not created'
                }
            
            source_size = os.path.getsize(source)
            dest_size = os.path.getsize(destination)
            
            if source_size != dest_size:
                return {
                    'success': False,
                    'error': f'Copy verification failed - size mismatch ({source_size} vs {dest_size})'
                }
            
            return {
                'success': True,
                'source_path': source,
                'destination_path': destination,
                'file_size': dest_size,
                'copied_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"File copy failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def move_file(self, source: str, destination: str, overwrite: bool = False) -> Dict[str, Any]:
        """
        Move file with validation and error handling
        
        Args:
            source: Source file path
            destination: Destination file path
            overwrite: Whether to overwrite existing destination
            
        Returns:
            Dict with move operation results
        """
        try:
            # First copy the file
            copy_result = self.copy_file(source, destination, overwrite)
            
            if not copy_result.get('success', False):
                return copy_result
            
            # Then remove the source
            os.remove(source)
            
            return {
                'success': True,
                'source_path': source,
                'destination_path': destination,
                'file_size': copy_result.get('file_size', 0),
                'moved_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"File move failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_file(self, file_path: str, force: bool = False) -> Dict[str, Any]:
        """
        Safely delete a file
        
        Args:
            file_path: Path to file to delete
            force: Force deletion even if file is not in temp directory
            
        Returns:
            Dict with cleanup results
        """
        try:
            if not os.path.exists(file_path):
                return {
                    'success': True,
                    'message': 'File already does not exist'
                }
            
            # Safety check - only delete files in temp directory unless forced
            if not force and not file_path.startswith(self.temp_dir):
                return {
                    'success': False,
                    'error': 'File is not in temporary directory - use force=True to delete'
                }
            
            file_info = self.get_file_info(file_path)
            os.remove(file_path)
            
            return {
                'success': True,
                'deleted_file': file_path,
                'file_size': file_info.get('size', 0),
                'deleted_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"File cleanup failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def read_file_sample(self, file_path: str, sample_size: int = 1024) -> Dict[str, Any]:
        """
        Read a sample of the file for analysis
        
        Args:
            file_path: Path to the file
            sample_size: Number of bytes to read
            
        Returns:
            Dict containing sample data and analysis
        """
        try:
            file_extension = Path(file_path).suffix.lower()
            
            if file_extension == '.csv':
                return self._sample_csv(file_path)
            elif file_extension in ['.xlsx', '.xls']:
                return self._sample_excel(file_path)
            elif file_extension == '.pdf':
                return self._sample_pdf(file_path)
            else:
                # Generic binary sample
                with open(file_path, 'rb') as f:
                    sample = f.read(sample_size)
                
                return {
                    'file_type': 'binary',
                    'sample_size': len(sample),
                    'sample_data': sample[:100],  # First 100 bytes
                    'is_text': self._is_text_file(sample)
                }
                
        except Exception as e:
            logger.error(f"Failed to read file sample: {str(e)}")
            return {'error': str(e)}
    
    def _sample_csv(self, file_path: str) -> Dict[str, Any]:
        """Sample CSV file structure"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            df = None
            used_encoding = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, nrows=5)
                    used_encoding = encoding
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                return {'error': 'Could not read CSV with any encoding'}
            
            return {
                'file_type': 'csv',
                'encoding': used_encoding,
                'columns': list(df.columns),
                'column_count': len(df.columns),
                'sample_rows': len(df),
                'data_types': df.dtypes.to_dict(),
                'sample_data': df.head(3).to_dict('records')
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _sample_excel(self, file_path: str) -> Dict[str, Any]:
        """Sample Excel file structure"""
        try:
            # Get sheet names
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            # Read first sheet sample
            df = pd.read_excel(file_path, sheet_name=sheet_names[0], nrows=5)
            
            return {
                'file_type': 'excel',
                'sheet_names': sheet_names,
                'sheet_count': len(sheet_names),
                'active_sheet': sheet_names[0],
                'columns': list(df.columns),
                'column_count': len(df.columns),
                'sample_rows': len(df),
                'data_types': df.dtypes.to_dict(),
                'sample_data': df.head(3).to_dict('records')
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _sample_pdf(self, file_path: str) -> Dict[str, Any]:
        """Sample PDF file structure"""
        try:
            sample_data = {}
            
            # Try pdfplumber first
            try:
                with pdfplumber.open(file_path) as pdf:
                    page_count = len(pdf.pages)
                    first_page = pdf.pages[0] if page_count > 0 else None
                    
                    sample_text = ""
                    tables_found = 0
                    
                    if first_page:
                        sample_text = first_page.extract_text()[:500]  # First 500 chars
                        tables = first_page.extract_tables()
                        tables_found = len(tables) if tables else 0
                    
                    sample_data.update({
                        'extraction_method': 'pdfplumber',
                        'page_count': page_count,
                        'tables_found': tables_found,
                        'sample_text': sample_text,
                        'has_tables': tables_found > 0
                    })
                    
            except Exception as e:
                # Fallback to PyPDF2
                try:
                    with open(file_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        page_count = len(pdf_reader.pages)
                        
                        sample_text = ""
                        if page_count > 0:
                            first_page = pdf_reader.pages[0]
                            sample_text = first_page.extract_text()[:500]
                        
                        sample_data.update({
                            'extraction_method': 'PyPDF2',
                            'page_count': page_count,
                            'sample_text': sample_text,
                            'fallback_reason': str(e)
                        })
                        
                except Exception as e2:
                    sample_data['error'] = f"Both PDF methods failed: {str(e2)}"
            
            sample_data['file_type'] = 'pdf'
            return sample_data
            
        except Exception as e:
            return {'error': str(e)}
    
    def _calculate_file_hash(self, file_path: str, algorithm: str = 'md5') -> str:
        """Calculate file hash for integrity checking"""
        try:
            hash_func = hashlib.new(algorithm)
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_func.update(chunk)
            
            return hash_func.hexdigest()
            
        except Exception as e:
            logger.error(f"Hash calculation failed: {str(e)}")
            return ""
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    def _is_text_file(self, sample: bytes) -> bool:
        """Check if file appears to be text based on sample"""
        try:
            sample.decode('utf-8')
            return True
        except UnicodeDecodeError:
            try:
                sample.decode('latin-1')
                return True
            except UnicodeDecodeError:
                return False

class SecureFileHandler(FileHandler):
    """Enhanced FileHandler with additional security features"""
    
    DANGEROUS_EXTENSIONS = {'.exe', '.bat', '.cmd', '.scr', '.vbs', '.js', '.jar'}
    
    def __init__(self, temp_dir: Optional[str] = None, enable_virus_scan: bool = False):
        """
        Initialize SecureFileHandler
        
        Args:
            temp_dir: Temporary directory for file operations
            enable_virus_scan: Whether to enable virus scanning (requires additional setup)
        """
        super().__init__(temp_dir)
        self.enable_virus_scan = enable_virus_scan
    
    def validate_file(self, file_path: str, max_size: Optional[int] = None) -> Dict[str, Any]:
        """
        Enhanced file validation with security checks
        
        Args:
            file_path: Path to the file to validate
            max_size: Maximum allowed file size in bytes
            
        Returns:
            Dict containing validation results with security analysis
        """
        # Run basic validation first
        result = super().validate_file(file_path, max_size)
        
        if not result.get('valid', False):
            return result
        
        try:
            # Additional security checks
            file_extension = Path(file_path).suffix.lower()
            
            # Check for dangerous extensions
            if file_extension in self.DANGEROUS_EXTENSIONS:
                result.update({
                    'valid': False,
                    'error': f'Potentially dangerous file type: {file_extension}',
                    'error_code': 'DANGEROUS_FILE_TYPE',
                    'security_risk': 'high'
                })
                return result
            
            # Check file content vs extension
            content_analysis = self._analyze_file_content(file_path, file_extension)
            if not content_analysis.get('content_matches_extension', True):
                result.update({
                    'security_warning': 'File content does not match extension',
                    'content_analysis': content_analysis,
                    'security_risk': 'medium'
                })
            
            # Virus scan if enabled
            if self.enable_virus_scan:
                scan_result = self._scan_file_for_threats(file_path)
                result['virus_scan'] = scan_result
                
                if scan_result.get('threats_detected', False):
                    result.update({
                        'valid': False,
                        'error': 'Security threats detected in file',
                        'error_code': 'SECURITY_THREAT',
                        'security_risk': 'high'
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Security validation failed: {str(e)}")
            result['security_error'] = str(e)
            return result
    
    def _analyze_file_content(self, file_path: str, expected_extension: str) -> Dict[str, Any]:
        """Analyze file content to verify it matches the claimed extension"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(512)  # Read first 512 bytes
            
            # Common file signatures
            signatures = {
                '.pdf': [b'%PDF'],
                '.xlsx': [b'PK\x03\x04'],  # ZIP-based formats
                '.xls': [b'\xd0\xcf\x11\xe0'],  # OLE format
                '.csv': []  # CSV doesn't have a specific signature
            }
            
            expected_sigs = signatures.get(expected_extension, [])
            
            if not expected_sigs:  # CSV or unknown format
                return {'content_matches_extension': True, 'analysis': 'No signature check available'}
            
            for sig in expected_sigs:
                if header.startswith(sig):
                    return {'content_matches_extension': True, 'matched_signature': sig.hex()}
            
            return {
                'content_matches_extension': False,
                'expected_signatures': [sig.hex() for sig in expected_sigs],
                'actual_header': header[:20].hex()
            }
            
        except Exception as e:
            return {'analysis_error': str(e)}
    
    def _scan_file_for_threats(self, file_path: str) -> Dict[str, Any]:
        """
        Placeholder for virus scanning functionality
        In a real implementation, this would integrate with antivirus APIs
        """
        # This is a placeholder - in production, you'd integrate with:
        # - ClamAV
        # - VirusTotal API
        # - Windows Defender API
        # - Other security scanning services
        
        return {
            'scan_performed': False,
            'threats_detected': False,
            'message': 'Virus scanning not implemented - placeholder only',
            'recommendation': 'Implement proper virus scanning for production use'
        }

# Create default instances
file_handler = FileHandler()
secure_file_handler = SecureFileHandler()