"""
Transaction service for managing transaction processing and analysis
"""
import structlog
from typing import List, Dict, Any, Optional
from app.models.transaction import Transaction, CategorizedTransaction
from app.models.insights import FinancialInsights, CategorySummary
from app.agents.team_manager import FinanceTeamManager
from app.services.file_processor import FileProcessor

logger = structlog.get_logger(__name__)


class TransactionService:
    """
    High-level service for transaction processing and analysis.
    Coordinates between file processing and AI agents.
    """
    
    def __init__(self):
        self.logger = logger.bind(service="TransactionService")
        self.file_processor = FileProcessor()
        self.team_manager = FinanceTeamManager()
        
        self.logger.info("Transaction service initialized")
    
    async def process_uploaded_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Process uploaded file and extract transactions
        
        Args:
            file_content: Raw file content
            filename: Original filename
            
        Returns:
            Processing result with extracted transactions
        """
        try:
            self.logger.info("Processing uploaded file", 
                           filename=filename, 
                           size=len(file_content))
            
            # Validate file first
            validation = self.file_processor.validate_file(file_content, filename)
            if not validation["valid"]:
                return {
                    "success": False,
                    "message": f"File validation failed: {', '.join(validation['errors'])}",
                    "transactions": [],
                    "total_transactions": 0,
                    "validation": validation
                }
            
            # Extract transactions from file
            transactions = await self.file_processor.process_file(file_content, filename)
            
            if not transactions:
                return {
                    "success": False,
                    "message": "No transactions found in the file. Please check the file format.",
                    "transactions": [],
                    "total_transactions": 0
                }
            
            # Store transactions in team manager
            self.team_manager._current_transactions = transactions
            
            self.logger.info("File processing completed", 
                           filename=filename,
                           transaction_count=len(transactions))
            
            return {
                "success": True,
                "message": f"Successfully processed {filename}. Transaction extraction completed by AI agent.",
                "transactions": transactions,
                "total_transactions": len(transactions),
                "file_info": {
                    "filename": filename,
                    "file_type": validation["file_type"],
                    "file_size": validation["file_size"],
                    "processing_method": "AI-powered extraction"
                }
            }
            
        except Exception as e:
            self.logger.error("File processing failed", 
                            filename=filename, 
                            error=str(e))
            return {
                "success": False,
                "message": f"Failed to process file: {str(e)}",
                "transactions": [],
                "total_transactions": 0
            }
    
    async def categorize_transactions(self) -> Dict[str, Any]:
        """
        Categorize previously uploaded transactions using AI team
        
        Returns:
            Categorization result
        """
        try:
            self.logger.info("Starting transaction categorization")
            
            # Check if we have transactions to categorize
            if not self.team_manager.current_transactions:
                return {
                    "success": False,
                    "message": "No transactions available for categorization. Please upload a file first.",
                    "categorized_transactions": [],
                    "category_summary": {},
                    "total_amount": 0.0
                }
            
            # Use team manager to process transactions
            result = await self.team_manager.process_transactions(
                self.team_manager.current_transactions
            )
            
            if not result["success"]:
                return result
            
            self.logger.info("Transaction categorization completed", 
                           categorized_count=len(result["categorized_transactions"]))
            
            return result
            
        except Exception as e:
            self.logger.error("Transaction categorization failed", error=str(e))
            return {
                "success": False,
                "message": f"Categorization failed: {str(e)}",
                "categorized_transactions": [],
                "category_summary": {},
                "total_amount": 0.0
            }
    
    async def generate_insights(self) -> Dict[str, Any]:
        """
        Generate financial insights from categorized transactions
        
        Returns:
            Insights generation result
        """
        try:
            self.logger.info("Starting insights generation")
            
            # Check if we have categorized transactions
            if not self.team_manager.categorized_transactions:
                return {
                    "success": False,
                    "message": "No categorized transactions available. Please upload and categorize transactions first.",
                    "insights": {}
                }
            
            # Generate insights using team manager
            result = await self.team_manager.generate_insights()
            
            return result
            
        except Exception as e:
            self.logger.error("Insights generation failed", error=str(e))
            return {
                "success": False,
                "message": f"Insights generation failed: {str(e)}",
                "insights": {}
            }
    
    async def complete_workflow(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Complete workflow: file processing -> categorization -> insights
        
        Args:
            file_content: Raw file content
            filename: Original filename
            
        Returns:
            Complete workflow result
        """
        try:
            self.logger.info("Starting complete workflow", filename=filename)
            
            # Step 1: Process file
            upload_result = await self.process_uploaded_file(file_content, filename)
            if not upload_result["success"]:
                return {
                    "success": False,
                    "message": "Workflow failed at file processing step",
                    "upload_result": upload_result,
                    "categorization_result": {},
                    "insights_result": {}
                }
            
            # Step 2: Categorize transactions
            categorization_result = await self.categorize_transactions()
            if not categorization_result["success"]:
                return {
                    "success": False,
                    "message": "Workflow failed at categorization step",
                    "upload_result": upload_result,
                    "categorization_result": categorization_result,
                    "insights_result": {}
                }
            
            # Step 3: Generate insights
            insights_result = await self.generate_insights()
            
            workflow_success = (upload_result["success"] and 
                              categorization_result["success"] and 
                              insights_result["success"])
            
            self.logger.info("Complete workflow finished", 
                           success=workflow_success,
                           filename=filename)
            
            return {
                "success": workflow_success,
                "message": "Complete workflow finished successfully" if workflow_success else "Workflow completed with some failures",
                "upload_result": upload_result,
                "categorization_result": categorization_result,
                "insights_result": insights_result,
                "workflow_summary": {
                    "total_transactions": upload_result.get("total_transactions", 0),
                    "categorized_transactions": len(categorization_result.get("categorized_transactions", [])),
                    "categories_found": len(categorization_result.get("category_summary", {})),
                    "insights_generated": bool(insights_result.get("insights"))
                }
            }
            
        except Exception as e:
            self.logger.error("Complete workflow failed", filename=filename, error=str(e))
            return {
                "success": False,
                "message": f"Workflow failed: {str(e)}",
                "upload_result": {},
                "categorization_result": {},
                "insights_result": {}
            }
    
    async def handle_user_correction(self, 
                                   transaction_index: int,
                                   correct_category: str,
                                   correct_subcategory: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle user correction and enable learning
        
        Args:
            transaction_index: Index of transaction to correct
            correct_category: Correct category
            correct_subcategory: Correct subcategory
            
        Returns:
            Correction handling result
        """
        try:
            self.logger.info("Handling user correction", 
                           transaction_index=transaction_index,
                           correct_category=correct_category)
            
            result = await self.team_manager.handle_user_correction(
                transaction_index,
                correct_category,
                correct_subcategory
            )
            
            return result
            
        except Exception as e:
            self.logger.error("User correction handling failed", error=str(e))
            return {
                "success": False,
                "message": f"Correction handling failed: {str(e)}"
            }
    
    def get_current_transactions(self) -> List[Transaction]:
        """Get currently loaded transactions"""
        return self.team_manager.current_transactions
    
    def get_categorized_transactions(self) -> List[CategorizedTransaction]:
        """Get categorized transactions"""
        return self.team_manager.categorized_transactions
    
    def get_category_summary(self) -> Dict[str, CategorySummary]:
        """Get category summary"""
        return self.team_manager.category_summary
    
    def get_last_insights(self) -> Optional[FinancialInsights]:
        """Get last generated insights"""
        return self.team_manager.last_insights
    
    def get_session_status(self) -> Dict[str, Any]:
        """
        Get current session status
        
        Returns:
            Session status information
        """
        current_transactions = self.team_manager.current_transactions
        categorized_transactions = self.team_manager.categorized_transactions
        
        return {
            "has_transactions": len(current_transactions) > 0,
            "has_categorized_data": len(categorized_transactions) > 0,
            "transaction_count": len(current_transactions),
            "ready_for_categorization": len(current_transactions) > 0,
            "ready_for_insights": len(categorized_transactions) > 0,
            "last_upload_time": None,  # Would be stored in a real session
            "last_categorization_time": None  # Would be stored in a real session
        }
    
    def reset_session(self):
        """Reset current session"""
        try:
            self.team_manager.reset_team_state()
            self.logger.info("Session reset completed")
            return {
                "success": True,
                "message": "Session reset successfully"
            }
        except Exception as e:
            self.logger.error("Session reset failed", error=str(e))
            return {
                "success": False,
                "message": f"Session reset failed: {str(e)}"
            }
    
    def get_supported_formats(self) -> Dict[str, Any]:
        """
        Get supported file formats and constraints
        
        Returns:
            Supported formats information
        """
        from app.config import get_settings
        settings = get_settings()
        
        return {
            "success": True,
            "supported_formats": settings.allowed_file_types,
            "max_file_size_mb": settings.max_file_size_mb,
            "features": [
                "CSV files with various delimiters",
                "Excel files (XLS and XLSX)",
                "PDF bank statements",
                "Indian bank format support",
                "Automatic column detection",
                "Multiple date format support"
            ]
        }
    
    def get_service_stats(self) -> Dict[str, Any]:
        """
        Get transaction service statistics
        
        Returns:
            Service statistics
        """
        team_status = self.team_manager.get_team_status()
        
        return {
            "service": "TransactionService",
            "file_processor": {
                "supported_formats": ["csv", "xlsx", "xls", "pdf"],
                "features": [
                    "Multi-format support",
                    "Indian bank patterns",
                    "Intelligent column mapping",
                    "Date format detection"
                ]
            },
            "ai_team": team_status,
            "current_session": self.get_session_status(),
            "capabilities": [
                "File processing and validation",
                "AI-powered transaction categorization",
                "Financial insights generation",
                "User correction learning",
                "Complete workflow automation"
            ]
        }