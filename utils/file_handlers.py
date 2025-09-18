"""
File handling utilities for Finance Manager

This module provides comprehensive file handling capabilities including:
- File validation and security checks
- File type detection and validation
- Secure file operations
- File size and format validation
- Upload directory management
"""

import os
import re
import mimetypes
import hashlib
from typing import Optional, Tuple, Dict, Any, List
from pathlib import Path
import magic
from werkzeug.utils import secure_filename as werkzeug_secure_filename

class FileTypeDetector:
    """Advanced file type detection using multiple methods"""
    
    MIME_TYPE_MAP = {
        'text/csv': '.csv',
        'application/vnd.ms-excel': '.xls',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
        'application/pdf': '.pdf',
        'text/plain': '.txt'
    }
    
    MAGIC_SIGNATURES = {
        b'\x50\x4B\x03\x04': '.xlsx',  # ZIP signature (xlsx files)
        b'\xD0\xCF\x11\xE0': '.xls',   # MS Office signature
        b'%PDF': '.pdf',               # PDF signature
    }
    
    @classmethod
    def detect_file_type(cls, file_content: bytes, filename: str) -> Tuple[str, float]:
        """
        Detect file type using multiple methods
        
        Args:
            file_content: Raw file content
            filename: Original filename
            
        Returns:
            Tuple of (file_extension, confidence_score)
        """
        confidence_scores = {}
        
        # Method 1: File extension
        ext_from_filename = cls._get_extension_from_filename(filename)
        if ext_from_filename:
            confidence_scores[ext_from_filename] = confidence_scores.get(ext_from_filename, 0) + 0.3
        
        # Method 2: MIME type detection
        try:
            mime_type = magic.from_buffer(file_content, mime=True)
            ext_from_mime = cls.MIME_TYPE_MAP.get(mime_type)
            if ext_from_mime:
                confidence_scores[ext_from_mime] = confidence_scores.get(ext_from_mime, 0) + 0.4
        except:
            pass
        
        # Method 3: Magic signatures
        ext_from_magic = cls._detect_by_magic_signature(file_content)
        if ext_from_magic:
            confidence_scores[ext_from_magic] = confidence_scores.get(ext_from_magic, 0) + 0.3
        
        # Method 4: Content analysis
        ext_from_content = cls._detect_by_content_analysis(file_content)
        if ext_from_content:
            confidence_scores[ext_from_content] = confidence_scores.get(ext_from_content, 0) + 0.2
        
        if confidence_scores:
            best_match = max(confidence_scores.items(), key=lambda x: x[1])
            return best_match[0], best_match[1]
        
        return '.unknown', 0.0
    
    @classmethod
    def _get_extension_from_filename(cls, filename: str) -> Optional[str]:
        """Extract file extension from filename"""
        return Path(filename).suffix.lower() if filename else None
    
    @classmethod
    def _detect_by_magic_signature(cls, file_content: bytes) -> Optional[str]:
        """Detect file type by magic signature"""
        for signature, extension in cls.MAGIC_SIGNATURES.items():
            if file_content.startswith(signature):
                return extension
        return None
    
    @classmethod
    def _detect_by_content_analysis(cls, file_content: bytes) -> Optional[str]:
        """Detect file type by analyzing content patterns"""
        try:
            # Try to decode as text for CSV detection
            text_content = file_content.decode('utf-8', errors='ignore')[:1000]
            
            # CSV patterns
            if cls._looks_like_csv(text_content):
                return '.csv'
                
            # PDF patterns
            if b'%PDF' in file_content[:100]:
                return '.pdf'
                
        except:
            pass
        
        return None
    
    @classmethod
    def _looks_like_csv(cls, text: str) -> bool:
        """Check if text content looks like CSV"""
        lines = text.split('\n')[:5]  # Check first 5 lines
        
        for line in lines:
            if line.strip():
                # Check for common CSV patterns
                if ',' in line and len(line.split(',')) > 1:
                    return True
                    
        return False


class FileValidator:
    """Comprehensive file validation"""
    
    ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.pdf'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MIN_FILE_SIZE = 10  # 10 bytes
    
    DANGEROUS_EXTENSIONS = {'.exe', '.bat', '.cmd', '.com', '.scr', '.vbs', '.js', '.jar', '.pif'}
    
    @classmethod
    def validate_file(cls, file_content: bytes, filename: str, max_size: Optional[int] = None) -> Dict[str, Any]:
        """
        Comprehensive file validation
        
        Args:
            file_content: Raw file content
            filename: Original filename
            max_size: Maximum allowed file size (optional)
            
        Returns:
            Dict with validation results
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'file_info': {},
            'security_check': True
        }
        
        # Basic validations
        if not file_content:
            validation_result['is_valid'] = False
            validation_result['errors'].append('File is empty')
            return validation_result
        
        if not filename:
            validation_result['is_valid'] = False
            validation_result['errors'].append('Filename is required')
            return validation_result
        
        # File size validation
        file_size = len(file_content)
        max_allowed_size = max_size or cls.MAX_FILE_SIZE
        
        if file_size < cls.MIN_FILE_SIZE:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f'File too small: {file_size} bytes')
        
        if file_size > max_allowed_size:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f'File too large: {file_size} bytes (max: {max_allowed_size} bytes)')
        
        # Security checks
        security_issues = cls._perform_security_checks(file_content, filename)
        if security_issues:
            validation_result['is_valid'] = False
            validation_result['security_check'] = False
            validation_result['errors'].extend(security_issues)
        
        # File type validation
        detected_type, confidence = FileTypeDetector.detect_file_type(file_content, filename)
        
        if detected_type not in cls.ALLOWED_EXTENSIONS:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f'Unsupported file type: {detected_type}')
        
        if confidence < 0.5:
            validation_result['warnings'].append(f'Low confidence in file type detection: {confidence:.2f}')
        
        # Store file information
        validation_result['file_info'] = {
            'filename': filename,
            'size': file_size,
            'detected_type': detected_type,
            'confidence': confidence,
            'secure_filename': secure_filename(filename)
        }
        
        return validation_result
    
    @classmethod
    def _perform_security_checks(cls, file_content: bytes, filename: str) -> List[str]:
        """Perform security checks on the file"""
        issues = []
        
        # Check for dangerous file extensions
        extension = Path(filename).suffix.lower()
        if extension in cls.DANGEROUS_EXTENSIONS:
            issues.append(f'Dangerous file extension: {extension}')
        
        # Check for executable signatures
        if cls._has_executable_signature(file_content):
            issues.append('File appears to be executable')
        
        # Check for suspicious patterns
        if cls._has_suspicious_patterns(file_content):
            issues.append('File contains suspicious patterns')
        
        return issues
    
    @classmethod
    def _has_executable_signature(cls, file_content: bytes) -> bool:
        """Check if file has executable signatures"""
        executable_signatures = [
            b'MZ',      # DOS/Windows executable
            b'\x7fELF', # Linux executable
            b'\xca\xfe\xba\xbe',  # Java class file
        ]
        
        for signature in executable_signatures:
            if file_content.startswith(signature):
                return True
        
        return False
    
    @classmethod
    def _has_suspicious_patterns(cls, file_content: bytes) -> bool:
        """Check for suspicious patterns in file content"""
        try:
            # Check first 1KB for suspicious patterns
            sample = file_content[:1024].decode('utf-8', errors='ignore').lower()
            
            suspicious_patterns = [
                'script',
                'javascript',
                'vbscript',
                'powershell',
                'cmd.exe',
                'system(',
                'exec(',
                'eval('
            ]
            
            for pattern in suspicious_patterns:
                if pattern in sample:
                    return True
                    
        except:
            pass
        
        return False


class FileHandler:
    """Main file handler class with comprehensive file operations"""
    
    def __init__(self, upload_dir: str = './uploads'):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def save_file(self, file_content: bytes, filename: str, validate: bool = True) -> Dict[str, Any]:
        """
        Save file with validation and security checks
        
        Args:
            file_content: Raw file content
            filename: Original filename
            validate: Whether to perform validation
            
        Returns:
            Dict with save results
        """
        result = {
            'success': False,
            'file_path': None,
            'file_id': None,
            'errors': [],
            'file_info': {}
        }
        
        try:
            # Validate file if requested
            if validate:
                validation = FileValidator.validate_file(file_content, filename)
                if not validation['is_valid']:
                    result['errors'] = validation['errors']
                    return result
                
                result['file_info'] = validation['file_info']
                filename = validation['file_info']['secure_filename']
            
            # Generate unique filename
            file_id = self._generate_file_id(file_content, filename)
            secure_name = f"{file_id}_{secure_filename(filename)}"
            file_path = self.upload_dir / secure_name
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            result.update({
                'success': True,
                'file_path': str(file_path),
                'file_id': file_id,
                'file_info': {
                    'original_filename': filename,
                    'secure_filename': secure_name,
                    'size': len(file_content),
                    'saved_at': str(file_path)
                }
            })
            
        except Exception as e:
            result['errors'].append(f'Error saving file: {str(e)}')
        
        return result
    
    def load_file(self, file_path: str) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Load file from disk
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (file_content, error_message)
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return None, f'File not found: {file_path}'
            
            if not path.is_file():
                return None, f'Path is not a file: {file_path}'
            
            with open(path, 'rb') as f:
                content = f.read()
            
            return content, None
            
        except Exception as e:
            return None, f'Error loading file: {str(e)}'
    
    def delete_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Delete file from disk
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                return True, None
            else:
                return False, f'File not found: {file_path}'
                
        except Exception as e:
            return False, f'Error deleting file: {str(e)}'
    
    def _generate_file_id(self, file_content: bytes, filename: str) -> str:
        """Generate unique file ID based on content hash"""
        hasher = hashlib.sha256()
        hasher.update(file_content)
        hasher.update(filename.encode('utf-8'))
        return hasher.hexdigest()[:16]
    
    def cleanup_old_files(self, days: int = 7) -> int:
        """
        Clean up files older than specified days
        
        Args:
            days: Number of days to keep files
            
        Returns:
            Number of files deleted
        """
        deleted_count = 0
        cutoff_time = Path().stat().st_mtime - (days * 24 * 60 * 60)
        
        try:
            for file_path in self.upload_dir.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except:
                        continue
        except Exception:
            pass
        
        return deleted_count


# Utility functions
def secure_filename(filename: str) -> str:
    """
    Make filename secure by removing/replacing dangerous characters
    
    Args:
        filename: Original filename
        
    Returns:
        Secure filename
    """
    if not filename:
        return 'unnamed_file'
    
    # Use werkzeug's secure_filename as base
    secure_name = werkzeug_secure_filename(filename)
    
    # Additional security measures
    secure_name = re.sub(r'[^\w\s\-_\.]', '', secure_name)
    secure_name = re.sub(r'[-\s]+', '_', secure_name)
    
    # Ensure filename is not empty and has reasonable length
    if not secure_name:
        secure_name = 'unnamed_file'
    
    if len(secure_name) > 100:
        name, ext = os.path.splitext(secure_name)
        secure_name = name[:95] + ext
    
    return secure_name


def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return Path(filename).suffix.lower() if filename else ''


def validate_file_size(file_size: int, max_size: Optional[int] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate file size
    
    Args:
        file_size: Size of file in bytes
        max_size: Maximum allowed size (optional)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    max_allowed = max_size or (10 * 1024 * 1024)  # 10MB default
    
    if file_size <= 0:
        return False, 'File is empty'
    
    if file_size > max_allowed:
        return False, f'File size {file_size} bytes exceeds maximum {max_allowed} bytes'
    
    return True, None


def create_upload_directory(directory: str) -> Tuple[bool, Optional[str]]:
    """
    Create upload directory with proper permissions
    
    Args:
        directory: Directory path to create
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return True, None
    except Exception as e:
        return False, f'Error creating directory: {str(e)}'