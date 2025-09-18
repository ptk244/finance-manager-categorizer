from typing import List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from agents.categorizer_agent import categorizer_agent
from models.response_models import APIResponse, CategorizationResponse
from models.transaction import ProcessedBankStatement, Transaction
from services.agent_team_service import agent_team_service

router = APIRouter(prefix="/categorize", tags=["Categorization"])

class CategorizationRequest(BaseModel):
    processed_statement: dict  # ProcessedBankStatement as dict
    force_recategorize: Optional[bool] = False

class SingleTransactionRequest(BaseModel):
    transaction: dict  # Transaction as dict
    force_category: Optional[str] = None

class BatchRecategorizeRequest(BaseModel):
    transactions: List[dict]  # List of transactions
    category_overrides: Optional[dict] = {}  # transaction_id -> category mapping

@router.post("/transactions", response_model=CategorizationResponse)
async def categorize_transactions(request: CategorizationRequest):
    """
    Categorize transactions in a processed bank statement
    
    Args:
        request: CategorizationRequest with processed statement data
    
    Returns:
        CategorizationResponse with categorized transactions
    """
    try:
        logger.info("Starting transaction categorization")
        
        # Convert dict to ProcessedBankStatement object
        try:
            processed_statement = ProcessedBankStatement(**request.processed_statement)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid processed statement format: {str(e)}"
            )
        
        # Categorize transactions
        categorization_result = await categorizer_agent.categorize_transactions(processed_statement)
        
        if not categorization_result.get('success', False):
            raise HTTPException(
                status_code=400,
                detail=f"Categorization failed: {categorization_result.get('error', 'Unknown error')}"
            )
        
        return CategorizationResponse(
            success=True,
            message="Transactions categorized successfully",
            data=categorization_result['categorized_statement']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Categorization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Categorization failed: {str(e)}")

@router.post("/transaction/single", response_model=APIResponse)
async def recategorize_single_transaction(request: SingleTransactionRequest):
    """
    Recategorize a single transaction
    
    Args:
        request: SingleTransactionRequest with transaction data and optional forced category
    
    Returns:
        APIResponse with recategorized transaction
    """
    try:
        logger.info("Recategorizing single transaction")
        
        # Convert dict to Transaction object
        try:
            transaction = Transaction(**request.transaction)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transaction format: {str(e)}"
            )
        
        # Recategorize transaction
        recategorization_result = await categorizer_agent.recategorize_transaction(
            transaction, 
            request.force_category
        )
        
        if not recategorization_result.get('success', False):
            raise HTTPException(
                status_code=400,
                detail=f"Recategorization failed: {recategorization_result.get('error', 'Unknown error')}"
            )
        
        return APIResponse(
            success=True,
            message="Transaction recategorized successfully",
            data={
                "updated_transaction": recategorization_result['transaction'],
                "method": recategorization_result.get('method', 'unknown')
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Single transaction recategorization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Recategorization failed: {str(e)}")

@router.post("/transactions/batch", response_model=APIResponse)
async def batch_recategorize_transactions(request: BatchRecategorizeRequest):
    """
    Batch recategorize multiple transactions with optional category overrides
    
    Args:
        request: BatchRecategorizeRequest with transactions and overrides
    
    Returns:
        APIResponse with batch recategorization results
    """
    try:
        logger.info(f"Batch recategorizing {len(request.transactions)} transactions")
        
        results = []
        
        for i, transaction_dict in enumerate(request.transactions):
            try:
                # Convert to Transaction object
                transaction = Transaction(**transaction_dict)
                
                # Check for category override
                transaction_id = str(i)  # Use index as ID
                forced_category = request.category_overrides.get(transaction_id)
                
                # Recategorize
                result = await categorizer_agent.recategorize_transaction(
                    transaction, 
                    forced_category
                )
                
                results.append({
                    "transaction_index": i,
                    "success": result.get('success', False),
                    "updated_transaction": result.get('transaction'),
                    "method": result.get('method', 'unknown'),
                    "error": result.get('error') if not result.get('success', False) else None
                })
                
            except Exception as e:
                logger.warning(f"Failed to recategorize transaction {i}: {str(e)}")
                results.append({
                    "transaction_index": i,
                    "success": False,
                    "error": str(e),
                    "updated_transaction": transaction_dict
                })
        
        successful_count = len([r for r in results if r['success']])
        
        return APIResponse(
            success=True,
            message=f"Batch recategorization completed: {successful_count}/{len(results)} successful",
            data={
                "results": results,
                "total_transactions": len(results),
                "successful_count": successful_count,
                "failed_count": len(results) - successful_count
            }
        )
        
    except Exception as e:
        logger.error(f"Batch recategorization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch recategorization failed: {str(e)}")

@router.get("/categories", response_model=APIResponse)
async def get_available_categories():
    """
    Get list of all available spending categories
    
    Returns:
        APIResponse with available categories
    """
    try:
        from models.transaction import SpendingCategory
        
        categories = [
            {
                "value": category.value,
                "name": category.name,
                "description": category.value.replace('_', ' ').title()
            }
            for category in SpendingCategory
        ]
        
        return APIResponse(
            success=True,
            message="Available categories retrieved successfully",
            data={
                "categories": categories,
                "total_count": len(categories)
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get categories: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")

@router.post("/summary", response_model=APIResponse)
async def get_category_summary(transactions: List[dict]):
    """
    Generate category-wise summary for a list of transactions
    
    Args:
        transactions: List of transaction dictionaries
    
    Returns:
        APIResponse with category summary
    """
    try:
        logger.info(f"Generating category summary for {len(transactions)} transactions")
        
        # Convert to Transaction objects
        transaction_objects = []
        for trans_dict in transactions:
            try:
                transaction = Transaction(**trans_dict)
                transaction_objects.append(transaction)
            except Exception as e:
                logger.warning(f"Skipping invalid transaction: {str(e)}")
                continue
        
        if not transaction_objects:
            raise HTTPException(
                status_code=400,
                detail="No valid transactions found"
            )
        
        # Generate summary
        summary = categorizer_agent.get_category_summary(transaction_objects)
        
        return APIResponse(
            success=True,
            message="Category summary generated successfully",
            data=summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Category summary generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Category summary failed: {str(e)}")

@router.get("/stats", response_model=APIResponse)
async def get_categorization_stats():
    """
    Get categorization performance statistics
    
    Returns:
        APIResponse with categorization statistics
    """
    try:
        # This could be enhanced to track actual statistics from a database
        # For now, return general information about the categorization system
        
        stats = {
            "categorization_methods": [
                {
                    "method": "AI-Powered (Gemini Pro)",
                    "description": "Uses advanced language model for context-aware categorization",
                    "accuracy": "85-95%"
                },
                {
                    "method": "Rule-Based Patterns",
                    "description": "Uses predefined patterns for common transaction types",
                    "accuracy": "70-85%"
                },
                {
                    "method": "Business Rules",
                    "description": "Applies financial logic and validation rules",
                    "accuracy": "90-100%"
                }
            ],
            "supported_categories": len([category for category in __import__('models.transaction', fromlist=['SpendingCategory']).SpendingCategory]),
            "confidence_levels": {
                "high": ">= 0.8",
                "medium": "0.5 - 0.8",
                "low": "< 0.5"
            },
            "features": [
                "Multi-method categorization",
                "Confidence scoring",
                "Manual override capability",
                "Batch processing",
                "Indian financial context awareness"
            ]
        }
        
        return APIResponse(
            success=True,
            message="Categorization statistics retrieved successfully",
            data=stats
        )
        
    except Exception as e:
        logger.error(f"Failed to get categorization stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")