"""
Finance Team Manager - Coordinates between Categorization and Insights agents using Agno Team
"""
import asyncio
import structlog
from typing import List, Dict, Any, Optional, Tuple
from agno.team import Team
from app.agents.categorization_agent import CategorizationAgent
from app.agents.insights_agent import InsightsAgent
from app.models.transaction import Transaction, CategorizedTransaction
from app.models.insights import FinancialInsights, CategorySummary
from app.config import get_agno_settings
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

def _serialize(data):
        """Recursively convert Pydantic models into dicts."""
        if isinstance(data, BaseModel):
            return data.model_dump()
        if isinstance(data, dict):
            return {k: _serialize(v) for k, v in data.items()}
        if isinstance(data, list):
            return [_serialize(v) for v in data]
        return data

class FinanceTeamManager:
    """
    Manages the finance team with specialized agents for different tasks.
    Coordinates workflow between categorization and insights generation.
    """
    
    def __init__(self):
        self.agno_settings = get_agno_settings()
        self.logger = logger.bind(component="FinanceTeamManager")
        
        # Initialize agents
        self.categorization_agent = CategorizationAgent()
        self.insights_agent = InsightsAgent()
        
        # Create Agno team
        self.team = Team(
            name=self.agno_settings.team_name,
            members=[self.categorization_agent, self.insights_agent],
            markdown=True
        )
        
        # Team state
        self._current_transactions: List[Transaction] = []
        self._categorized_transactions: List[CategorizedTransaction] = []
        self._category_summary: Dict[str, CategorySummary] = {}
        self._last_insights: Optional[FinancialInsights] = None
        
        self.logger.info("Finance team initialized",
                        team_name=self.agno_settings.team_name,
                        agents=[agent.name for agent in self.team.members])
        

    
    
    async def process_transactions(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """
        Process transactions through the complete workflow:
        1. Store transactions
        2. Categorize using CategorizationAgent
        3. Generate summary statistics
        
        Args:
            transactions: List of transactions to process
            
        Returns:
            Processing result with categorized transactions
        """
        try:
            self.logger.info("Starting transaction processing workflow", 
                           transaction_count=len(transactions))
            
            # Store transactions
            self._current_transactions = transactions
            
            # Step 1: Categorize transactions using CategorizationAgent
            self.logger.info("Step 1: Categorizing transactions")
            categorized_transactions = await self.categorization_agent.categorize_transactions(transactions)
            
            if not categorized_transactions:
                return {
                    "success": False,
                    "message": "Failed to categorize transactions",
                    "categorized_transactions": [],
                    "category_summary": {},
                    "total_amount": 0.0
                }
            
            # Store categorized results
            self._categorized_transactions = categorized_transactions
            
            # Step 2: Generate category summary
            self.logger.info("Step 2: Generating category summary")
            category_summary = self._generate_category_summary(categorized_transactions)
            self._category_summary = category_summary
            
            # Calculate totals
            total_amount = sum(txn.amount for txn in categorized_transactions if txn.type == 'debit')
            
            self.logger.info("Transaction processing completed successfully",
                           categorized_count=len(categorized_transactions),
                           categories=len(category_summary),
                           total_amount=total_amount)
            
            return _serialize({
                "success": True,
                "message": f"Successfully categorized {len(categorized_transactions)} transactions",
                "categorized_transactions": categorized_transactions,
                "category_summary": category_summary,
                "total_amount": total_amount,
                "processing_info": {
                    "categorization_agent": self.categorization_agent.name,
                    "model_used": getattr(self.categorization_agent.model, "model_name", "unknown"),
                    "categories_detected": len(category_summary),
                },
            })

            
        except Exception as e:
            self.logger.error("Transaction processing failed", error=str(e))
            return {
                "success": False,
                "message": f"Processing failed: {str(e)}",
                "categorized_transactions": [],
                "category_summary": {},
                "total_amount": 0.0
            }
    
    async def generate_insights(self) -> Dict[str, Any]:
        """
        Generate comprehensive financial insights using InsightsAgent
        
        Returns:
            Insights generation result
        """
        try:
            self.logger.info("Starting insights generation")
            
            if not self._categorized_transactions:
                return {
                    "success": False,
                    "message": "No categorized transactions available. Please upload and categorize transactions first.",
                    "insights": {}
                }
            
            # Generate insights using InsightsAgent
            insights = await self.insights_agent.generate_insights(
                self._categorized_transactions,
                self._category_summary
            )
            
            # Store insights
            self._last_insights = insights
            
            self.logger.info("Insights generation completed successfully")
            
            return {
                "success": True,
                "message": "Insights generated successfully",
                "insights": insights
            }
            
        except Exception as e:
            self.logger.error("Insights generation failed", error=str(e))
            return {
                "success": False,
                "message": f"Insights generation failed: {str(e)}",
                "insights": {}
            }
    
    async def process_and_analyze(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """
        Complete workflow: process transactions and generate insights
        
        Args:
            transactions: List of transactions to process
            
        Returns:
            Complete processing and analysis result
        """
        try:
            self.logger.info("Starting complete workflow", 
                           transaction_count=len(transactions))
            
            # Step 1: Process transactions (categorization)
            processing_result = await self.process_transactions(transactions)
            
            if not processing_result["success"]:
                return processing_result
            
            # Step 2: Generate insights
            insights_result = await self.generate_insights()
            
            # Combine results
            complete_result = {
                "success": True,
                "message": "Complete analysis finished successfully",
                "processing": processing_result,
                "insights": insights_result["insights"] if insights_result["success"] else {},
                "workflow_info": {
                    "categorization_agent": self.categorization_agent.name,
                    "insights_agent": self.insights_agent.name,
                    "team_name": self.team.name,
                    "total_transactions": len(transactions),
                    "workflow_steps": ["categorization", "summary_generation", "insights_generation"]
                }
            }
            
            self.logger.info("Complete workflow finished successfully")
            return complete_result
            
        except Exception as e:
            self.logger.error("Complete workflow failed", error=str(e))
            return {
                "success": False,
                "message": f"Workflow failed: {str(e)}",
                "processing": {},
                "insights": {}
            }
    
    async def team_collaboration(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enable team collaboration on complex tasks
        
        Args:
            task: Task description
            context: Task context and data
            
        Returns:
            Collaboration result
        """
        try:
            self.logger.info("Starting team collaboration", task=task)
            
            # Create collaboration prompt
            collaboration_prompt = f"""
            Team Task: {task}
            
            Context: {context}
            
            Please work together to complete this financial analysis task.
            CategorizationAgent should handle transaction categorization aspects.
            InsightsAgent should handle analysis and insights generation.
            
            Coordinate your responses to provide comprehensive results.
            """
            
            # Run team collaboration
            response = await self.team.arun(collaboration_prompt)
            
            return {
                "success": True,
                "task": task,
                "response": response.content,
                "participating_agents": [agent.name for agent in self.team.agents]
            }
            
        except Exception as e:
            self.logger.error("Team collaboration failed", error=str(e), task=task)
            return {
                "success": False,
                "message": f"Team collaboration failed: {str(e)}",
                "task": task
            }
    
    def _generate_category_summary(self, transactions: List[CategorizedTransaction]) -> Dict[str, CategorySummary]:
        """
        Generate category-wise summary statistics
        
        Args:
            transactions: List of categorized transactions
            
        Returns:
            Dictionary mapping categories to their summaries
        """
        category_data = {}
        total_amount = sum(txn.amount for txn in transactions if txn.type == 'debit')
        
        # Group transactions by category
        for txn in transactions:
            if txn.type != 'debit':  # Only consider debit transactions for spending analysis
                continue
                
            category = txn.category
            if category not in category_data:
                category_data[category] = []
            
            category_data[category].append(txn)
        
        # Generate summaries
        category_summaries = {}
        for category, txns in category_data.items():
            category_total = sum(txn.amount for txn in txns)
            percentage = (category_total / total_amount * 100) if total_amount > 0 else 0
            
            summary = CategorySummary(
                total_amount=category_total,
                transaction_count=len(txns),
                percentage=percentage,
                transactions=txns
            )
            
            category_summaries[category] = summary
        
        return category_summaries
    
    async def handle_user_correction(self, 
                                   transaction_index: int,
                                   correct_category: str,
                                   correct_subcategory: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle user corrections and enable agent learning
        
        Args:
            transaction_index: Index of transaction to correct
            correct_category: Correct category
            correct_subcategory: Correct subcategory
            
        Returns:
            Correction handling result
        """
        try:
            if not self._categorized_transactions or transaction_index >= len(self._categorized_transactions):
                return {
                    "success": False,
                    "message": "Invalid transaction index"
                }
            
            transaction = self._categorized_transactions[transaction_index]
            
            self.logger.info("Handling user correction",
                           transaction_index=transaction_index,
                           original_category=transaction.category,
                           correct_category=correct_category)
            
            # Let the categorization agent learn from the correction
            learning_result = await self.categorization_agent.learn_from_correction(
                transaction,
                correct_category,
                correct_subcategory
            )
            
            # Update the transaction
            transaction.category = correct_category
            if correct_subcategory:
                transaction.subcategory = correct_subcategory
            transaction.confidence = 1.0  # User correction has perfect confidence
            transaction.reasoning = f"User correction from {transaction.category}"
            
            # Regenerate category summary
            self._category_summary = self._generate_category_summary(self._categorized_transactions)
            
            return {
                "success": True,
                "message": "Correction applied and learned",
                "learning_result": learning_result,
                "updated_transaction": transaction
            }
            
        except Exception as e:
            self.logger.error("User correction handling failed", error=str(e))
            return {
                "success": False,
                "message": f"Correction handling failed: {str(e)}"
            }
    
    def get_team_status(self) -> Dict[str, Any]:
        """
        Get current team status and statistics
        
        Returns:
            Team status information
        """
        return {
            "team_name": self.team.name,
            "agents": [
                {
                    "name": agent.name,
                    "role": getattr(agent, 'role', 'Unknown'),
                    "model": agent.model.model_name if hasattr(agent.model, 'model_name') else 'Unknown',
                    "stats": agent.get_categorization_stats() if hasattr(agent, 'get_categorization_stats') 
                            else agent.get_insights_stats() if hasattr(agent, 'get_insights_stats')
                            else {}
                }
                for agent in self.team.agents
            ],
            "current_state": {
                "has_transactions": len(self._current_transactions) > 0,
                "has_categorized_data": len(self._categorized_transactions) > 0,
                "has_insights": self._last_insights is not None,
                "transaction_count": len(self._current_transactions),
                "categorized_count": len(self._categorized_transactions),
                "categories_found": len(self._category_summary)
            },
            "capabilities": [
                "Transaction categorization using Gemini Pro",
                "Financial insights generation using Gemini Flash", 
                "Team collaboration workflows",
                "User correction learning",
                "Category-wise analysis",
                "Anomaly detection",
                "Spending predictions"
            ]
        }
    
    def reset_team_state(self):
        """Reset team state for new processing session"""
        self._current_transactions = []
        self._categorized_transactions = []
        self._category_summary = {}
        self._last_insights = None
        
        self.logger.info("Team state reset completed")
    
    # Property accessors for current data
    @property
    def current_transactions(self) -> List[Transaction]:
        """Get current transactions"""
        return self._current_transactions.copy()
    
    @property
    def categorized_transactions(self) -> List[CategorizedTransaction]:
        """Get categorized transactions"""
        return self._categorized_transactions.copy()
    
    @property
    def category_summary(self) -> Dict[str, CategorySummary]:
        """Get category summary"""
        return self._category_summary.copy()
    
    @property
    def last_insights(self) -> Optional[FinancialInsights]:
        """Get last generated insights"""
        return self._last_insights