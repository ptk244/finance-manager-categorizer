import os
import uuid
from typing import Optional

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from loguru import logger

from config.settings import settings
from models.response_models import (APIResponse, FileUploadResponse,
                                    ProcessingResponse)
from services.agent_team_service import agent_team_service

router = APIRouter(prefix="/upload", tags=["File Upload"])

# Ensure upload directory exists
os.makedirs(settings.upload_dir, exist_ok=True)

def validate_file_extension(filename: str) -> bool:
    """Validate if file extension is allowed"""
    file_extension = os.path.splitext(filename)[1].lower()
    return file_extension in settings.allowed_extensions

def validate_file_size(file_size: int) -> bool:
    """Validate if file size is within limits"""
    max_size_bytes = 50 * 1024 * 1024  # 50MB
    return file_size <= max_size_bytes

@router.post("/", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    process_immediately: Optional[bool] = False
):
    """
    Upload bank statement file (CSV, Excel, or PDF)
    
    Args:
        file: Bank statement file
        process_immediately: Whether to process the file immediately after upload
    
    Returns:
        FileUploadResponse with upload status and optional processing results
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        if not validate_file_extension(file.filename):
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format. Allowed formats: {', '.join(settings.allowed_extensions)}"
            )
        
        # Read file content
        file_content = await file.read()
        
        if not validate_file_size(len(file_content)):
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {settings.max_file_size}"
            )
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{file_id}{file_extension}"
        file_path = os.path.join(settings.upload_dir, unique_filename)
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        logger.info(f"File uploaded successfully: {file.filename} -> {unique_filename}")
        
        response_data = {
            "file_id": file_id,
            "original_filename": file.filename,
            "uploaded_filename": unique_filename,
            "file_size": len(file_content),
            "file_type": file_extension,
            "upload_path": file_path
        }
        
        # Process immediately if requested
        if process_immediately:
            logger.info("Processing file immediately after upload")
            processing_result = await agent_team_service.process_file_only(file_path, file.filename)
            
            response_data["processing_result"] = processing_result
            response_data["processed_immediately"] = True
        
        return FileUploadResponse(
            success=True,
            message="File uploaded successfully",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@router.post("/process/{file_id}", response_model=ProcessingResponse)
async def process_uploaded_file(file_id: str):
    """
    Process a previously uploaded file
    
    Args:
        file_id: Unique file identifier from upload
    
    Returns:
        ProcessingResponse with extracted transaction data
    """
    try:
        # Find uploaded file
        file_found = False
        file_path = None
        original_filename = None
        
        for filename in os.listdir(settings.upload_dir):
            if filename.startswith(file_id):
                file_path = os.path.join(settings.upload_dir, filename)
                original_filename = filename
                file_found = True
                break
        
        if not file_found:
            raise HTTPException(
                status_code=404,
                detail=f"File with ID {file_id} not found"
            )
        
        logger.info(f"Processing file: {original_filename}")
        
        # Process the file
        processing_result = await agent_team_service.process_file_only(file_path, original_filename)
        
        if not processing_result.get('success', False):
            raise HTTPException(
                status_code=400,
                detail=f"File processing failed: {processing_result.get('error', 'Unknown error')}"
            )
        
        return ProcessingResponse(
            success=True,
            message="File processed successfully",
            data=processing_result['processed_statement']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")

@router.post("/complete-workflow/{file_id}", response_model=APIResponse)
async def complete_workflow(file_id: str):
    """
    Execute complete workflow: process file, categorize transactions, and generate insights
    
    Args:
        file_id: Unique file identifier from upload
    
    Returns:
        APIResponse with complete analysis results
    """
    try:
        # Find uploaded file
        file_found = False
        file_path = None
        original_filename = None
        
        for filename in os.listdir(settings.upload_dir):
            if filename.startswith(file_id):
                file_path = os.path.join(settings.upload_dir, filename)
                original_filename = filename
                file_found = True
                break
        
        if not file_found:
            raise HTTPException(
                status_code=404,
                detail=f"File with ID {file_id} not found"
            )
        
        logger.info(f"Starting complete workflow for: {original_filename}")
        
        # Execute complete workflow
        workflow_result = await agent_team_service.process_complete_workflow(file_path, original_filename)
        
        if not workflow_result.get('success', False):
            raise HTTPException(
                status_code=400,
                detail=f"Workflow execution failed: {workflow_result.get('error', 'Unknown error')}"
            )
        
        return APIResponse(
            success=True,
            message="Complete workflow executed successfully",
            data=workflow_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Complete workflow failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Complete workflow failed: {str(e)}")

@router.get("/files")
async def list_uploaded_files():
    """
    List all uploaded files
    
    Returns:
        List of uploaded files with metadata
    """
    try:
        files = []
        
        if os.path.exists(settings.upload_dir):
            for filename in os.listdir(settings.upload_dir):
                file_path = os.path.join(settings.upload_dir, filename)
                if os.path.isfile(file_path):
                    file_stats = os.stat(file_path)
                    
                    # Extract file ID from filename
                    file_id = filename.split('.')[0] if '.' in filename else filename
                    
                    files.append({
                        "file_id": file_id,
                        "filename": filename,
                        "size": file_stats.st_size,
                        "upload_time": file_stats.st_ctime,
                        "file_path": file_path
                    })
        
        return APIResponse(
            success=True,
            message=f"Found {len(files)} uploaded files",
            data={"files": files, "count": len(files)}
        )
        
    except Exception as e:
        logger.error(f"Failed to list files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@router.delete("/files/{file_id}")
async def delete_uploaded_file(file_id: str):
    """
    Delete an uploaded file
    
    Args:
        file_id: Unique file identifier
    
    Returns:
        APIResponse confirming deletion
    """
    try:
        file_found = False
        file_path = None
        
        for filename in os.listdir(settings.upload_dir):
            if filename.startswith(file_id):
                file_path = os.path.join(settings.upload_dir, filename)
                file_found = True
                break
        
        if not file_found:
            raise HTTPException(
                status_code=404,
                detail=f"File with ID {file_id} not found"
            )
        
        os.remove(file_path)
        logger.info(f"File deleted: {file_path}")
        
        return APIResponse(
            success=True,
            message="File deleted successfully",
            data={"deleted_file_id": file_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File deletion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File deletion failed: {str(e)}")