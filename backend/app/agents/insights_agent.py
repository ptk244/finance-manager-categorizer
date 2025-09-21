"""
Insights Agent - Specializes in generating financial insights using Gemini Flash
"""
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.agents.base_agent import BaseFinanceAgent
from app.models.transaction import CategorizedTransaction
from app.models.insights import FinancialInsights, CategorySummary, SpendingBehavior, FinancialHealth, StatisticalInsights, InsightMetadata
from app.config import get_settings,get_agno_settings


class InsightsAgent(BaseFinanceAgent):
    """
    AI Agent specialized in generating comprehensive financial insights.
    Uses Gemini Flash model for fast and efficient insights generation.
    """
    
    def __init__(self):
        settings = get_settings()
        AgnoSettings=get_agno_settings()
        
        role = "Expert Financial Analysis and Insights Specialist"
        
        instructions = """
        You are an expert AI agent specializing in financial analysis and insights generation.
        
        YOUR EXPERTISE:
        - Financial pattern recognition
        - Spending behavior analysis  
        - Risk assessment and recommendations
        - Savings optimization strategies
        - Investment guidance
        - Budget planning insights
        - Financial health assessment
        
        ANALYSIS FRAMEWORK:
        1. Spending Pattern Analysis
        2. Income vs Expense Analysis
        3. Category-wise Distribution
        4. Savings Rate Calculation
        5. Financial Health Scoring
        6. Trend Identification
        7. Actionable Recommendations
        
        INSIGHT GENERATION RULES:
        - Provide specific, actionable recommendations
        - Include quantitative metrics wherever possible
        - Consider Indian financial context and practices
        - Focus on practical, achievable goals
        - Highlight both strengths and areas for improvement
        - Use clear, non-technical language
        
        RESPONSE FORMAT:
        Always respond with valid JSON containing comprehensive insights:
        {
            "key_insights": ["List of 5-7 key insights"],
            "spending_behavior": {
                "total_spending": float,
                "total_income": float,
                "net_savings": float,
                "transaction_count": int
            },
            "recommendations": ["List of actionable recommendations"],
            "financial_health": {
                "status": "Excellent/Good/Fair/Needs Improvement",
                "savings_rate": "X.X%",
                "note": "Health assessment explanation"
            },
            "statistical_insights": {
                "income_spending_ratio": float,
                "ratio_comment": "Analysis of spending ratio",
                "top_category_concentration": float,
                "concentration_comment": "Spending concentration analysis",
                "transaction_pattern": "Pattern description",
                "savings_assessment": "Savings behavior analysis"
            }
        }
        
        FINANCIAL HEALTH SCORING:
        - Excellent: Savings rate > 40%, well-diversified spending
        - Good: Savings rate 20-40%, controlled spending
        - Fair: Savings rate 10-20%, some overspending areas
        - Needs Improvement: Savings rate < 10%, spending concerns
        
        Always provide valuable, actionable insights that help users improve their financial health.
        """
        
        super().__init__(
            name=AgnoSettings.insights_agent_name,
            model_name=settings.insights_model,
            role=role,
            instructions=instructions
        )
    
    async def generate_insights(self, 
                              categorized_transactions: List[CategorizedTransaction],
                              category_summary: Dict[str, CategorySummary]) -> FinancialInsights:
        """
        Generate comprehensive financial insights from categorized transactions
        
        Args:
            categorized_transactions: List of categorized transactions
            category_summary: Summary statistics by category
            
        Returns:
            Comprehensive financial insights
        """
        if not self.validate_input(categorized_transactions):
            return self._create_empty_insights()
        
        try:
            self.logger.info("Starting insights generation", 
                           transaction_count=len(categorized_transactions))
            
            # Calculate basic metrics
            financial_metrics = self._calculate_financial_metrics(categorized_transactions)
            category_analysis = self._analyze_categories(category_summary)
            
            # Create comprehensive data for analysis
            analysis_data = {
                "financial_metrics": financial_metrics,
                "category_analysis": category_analysis,
                "transaction_count": len(categorized_transactions),
                "date_range": self._get_date_range(categorized_transactions),
                "top_transactions": self._get_top_transactions(categorized_transactions)
            }
            
            # Generate insights prompt
            insights_prompt = f"""
            Please analyze the following financial data and generate comprehensive insights:
            
            FINANCIAL OVERVIEW:
            Total Income: ₹{financial_metrics['total_income']:,.2f}
            Total Spending: ₹{financial_metrics['total_spending']:,.2f}
            Net Savings: ₹{financial_metrics['net_savings']:,.2f}
            Savings Rate: {financial_metrics['savings_rate']:.1f}%
            Transaction Count: {len(categorized_transactions)}
            Analysis Period: {analysis_data['date_range']}
            
            SPENDING BREAKDOWN BY CATEGORY:
            {json.dumps(category_analysis, indent=2)}
            
            TOP TRANSACTIONS:
            {json.dumps(analysis_data['top_transactions'], indent=2)}
            
            Please provide detailed financial insights, recommendations, and health assessment.
            Focus on actionable advice for improving financial health and optimizing spending.
            """
            
            # Get insights from the agent
            response = await self.arun(insights_prompt)
            insights_data = self.parse_json_response(response.content)
            
            if "error" in insights_data:
                self.logger.error("Insights generation failed", error=insights_data)
                return self._create_fallback_insights(financial_metrics, category_analysis)
            
            # Create structured insights
            financial_insights = self._build_insights_object(
                insights_data, 
                financial_metrics,
                len(categorized_transactions),
                analysis_data['date_range']
            )
            
            self.logger.info("Insights generation completed successfully")
            return financial_insights
            
        except Exception as e:
            self.logger.error("Insights generation failed", error=str(e))
            financial_metrics = self._calculate_financial_metrics(categorized_transactions)
            category_analysis = self._analyze_categories(category_summary)
            return self._create_fallback_insights(financial_metrics, category_analysis)
    
    def _calculate_financial_metrics(self, transactions: List[CategorizedTransaction]) -> Dict[str, Any]:
        """Calculate basic financial metrics"""
        total_income = sum(t.amount for t in transactions if t.type == 'credit')
        total_spending = sum(t.amount for t in transactions if t.type == 'debit')
        net_savings = total_income - total_spending
        savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0
        
        return {
            "total_income": total_income,
            "total_spending": total_spending,
            "net_savings": net_savings,
            "savings_rate": savings_rate
        }
    
    def _analyze_categories(self, category_summary: Dict[str, CategorySummary]) -> Dict[str, Any]:
        """Analyze category spending patterns"""
        if not category_summary:
            return {}
        
        # Get top spending categories
        sorted_categories = sorted(
            category_summary.items(),
            key=lambda x: x[1].total_amount,
            reverse=True
        )
        
        analysis = {}
        for category, summary in sorted_categories[:5]:  # Top 5 categories
            analysis[category] = {
                "amount": summary.total_amount,
                "percentage": summary.percentage,
                "transaction_count": summary.transaction_count,
                "average_amount": summary.average_amount
            }
        
        return analysis
    
    def _get_date_range(self, transactions: List[CategorizedTransaction]) -> str:
        """Get the date range of transactions"""
        if not transactions:
            return "No transactions"
        
        dates = []
        for txn in transactions:
            if hasattr(txn.transaction_date, 'strftime'):
                dates.append(txn.transaction_date)
            elif isinstance(txn.transaction_date, str):
                try:
                    from datetime import datetime
                    parsed_date = datetime.strptime(txn.transaction_date, "%Y-%m-%d").date()
                    dates.append(parsed_date)
                except:
                    continue
        
        if not dates:
            return "Date range unavailable"
        
        min_date = min(dates)
        max_date = max(dates)
        
        return f"{min_date} to {max_date}"
    
    def _get_top_transactions(self, transactions: List[CategorizedTransaction], limit: int = 5) -> List[Dict[str, Any]]:
        """Get top transactions by amount"""
        sorted_transactions = sorted(transactions, key=lambda x: x.amount, reverse=True)
        
        top_transactions = []
        for txn in sorted_transactions[:limit]:
            top_transactions.append({
                "date": str(txn.transaction_date),
                "description": txn.description,
                "amount": txn.amount,
                "category": txn.category,
                "type": txn.type
            })
        
        return top_transactions
    
    def _build_insights_object(self, 
                              insights_data: Dict[str, Any],
                              financial_metrics: Dict[str, Any],
                              transaction_count: int,
                              date_range: str) -> FinancialInsights:
        """Build the FinancialInsights object from AI response"""
        
        # Extract or create spending behavior
        spending_behavior = SpendingBehavior(
            total_spending=financial_metrics["total_spending"],
            total_income=financial_metrics["total_income"],
            net_savings=financial_metrics["net_savings"],
            transaction_count=transaction_count
        )
        
        # Extract or create financial health
        health_data = insights_data.get("financial_health", {})
        financial_health = FinancialHealth(
            status=health_data.get("status", "Fair"),
            savings_rate=health_data.get("savings_rate", f"{financial_metrics['savings_rate']:.1f}%"),
            note=health_data.get("note", "Financial health assessment")
        )
        
        # Extract or create statistical insights
        stats_data = insights_data.get("statistical_insights", {})
        statistical_insights = StatisticalInsights(
            income_spending_ratio=stats_data.get("income_spending_ratio", 
                                                financial_metrics["total_spending"] / financial_metrics["total_income"] if financial_metrics["total_income"] > 0 else 0),
            ratio_comment=stats_data.get("ratio_comment", "Spending ratio analysis"),
            top_category_concentration=stats_data.get("top_category_concentration", 0.0),
            concentration_comment=stats_data.get("concentration_comment", "Spending concentration analysis"),
            transaction_pattern=stats_data.get("transaction_pattern", "Transaction pattern analysis"),
            savings_assessment=stats_data.get("savings_assessment", "Savings behavior assessment")
        )
        
        # Create metadata
        metadata = InsightMetadata(
            total_transactions=transaction_count,
            analysis_period=date_range,
            generated_at=datetime.now().isoformat(),
            model_used=self.model.model_name if hasattr(self.model, 'model_name') else self.settings.insights_model
        )
        
        # Build complete insights
        return FinancialInsights(
            key_insights=insights_data.get("key_insights", [
                f"Total spending: ₹{financial_metrics['total_spending']:,.2f}",
                f"Total income: ₹{financial_metrics['total_income']:,.2f}",
                f"Savings rate: {financial_metrics['savings_rate']:.1f}%",
                f"Transaction count: {transaction_count}",
                f"Analysis period: {date_range}"
            ]),
            spending_behavior=spending_behavior,
            recommendations=insights_data.get("recommendations", [
                "Track your expenses regularly",
                "Create a budget for major categories",
                "Look for opportunities to reduce spending",
                "Consider increasing your savings rate"
            ]),
            financial_health=financial_health,
            statistical_insights=statistical_insights,
            metadata=metadata
        )
    
    def _create_fallback_insights(self, 
                                financial_metrics: Dict[str, Any],
                                category_analysis: Dict[str, Any]) -> FinancialInsights:
        """Create fallback insights when AI processing fails"""
        
        self.logger.info("Creating fallback insights")
        
        # Basic spending behavior
        spending_behavior = SpendingBehavior(
            total_spending=financial_metrics["total_spending"],
            total_income=financial_metrics["total_income"],
            net_savings=financial_metrics["net_savings"],
            transaction_count=0
        )
        
        # Basic health assessment
        savings_rate = financial_metrics["savings_rate"]
        if savings_rate > 40:
            status = "Excellent"
        elif savings_rate > 20:
            status = "Good"
        elif savings_rate > 10:
            status = "Fair"
        else:
            status = "Needs Improvement"
        
        financial_health = FinancialHealth(
            status=status,
            savings_rate=f"{savings_rate:.1f}%",
            note=f"Automated assessment based on {savings_rate:.1f}% savings rate"
        )
        
        # Basic statistical insights
        income_spending_ratio = financial_metrics["total_spending"] / financial_metrics["total_income"] if financial_metrics["total_income"] > 0 else 0
        
        statistical_insights = StatisticalInsights(
            income_spending_ratio=income_spending_ratio,
            ratio_comment=f"You spend {income_spending_ratio:.1%} of your income",
            top_category_concentration=0.0,
            concentration_comment="Category analysis unavailable",
            transaction_pattern="Pattern analysis unavailable",
            savings_assessment=f"Savings rate of {savings_rate:.1f}% indicates {status.lower()} financial discipline"
        )
        
        # Basic metadata
        metadata = InsightMetadata(
            total_transactions=0,
            analysis_period="Analysis period unavailable",
            generated_at=datetime.now().isoformat(),
            model_used="fallback"
        )
        
        return FinancialInsights(
            key_insights=[
                f"Total spending: ₹{financial_metrics['total_spending']:,.2f}",
                f"Total income: ₹{financial_metrics['total_income']:,.2f}",
                f"Net savings: ₹{financial_metrics['net_savings']:,.2f}",
                f"Savings rate: {savings_rate:.1f}%",
                "Analysis generated using fallback method"
            ],
            spending_behavior=spending_behavior,
            recommendations=[
                "Review your spending patterns regularly",
                "Set up a monthly budget",
                "Track expenses by category",
                "Look for ways to optimize spending"
            ],
            financial_health=financial_health,
            statistical_insights=statistical_insights,
            metadata=metadata
        )
    
    def _create_empty_insights(self) -> FinancialInsights:
        """Create empty insights for invalid input"""
        return FinancialInsights(
            key_insights=["No transaction data available for analysis"],
            spending_behavior=SpendingBehavior(
                total_spending=0,
                total_income=0,
                net_savings=0,
                transaction_count=0
            ),
            recommendations=["Upload transaction data to get insights"],
            financial_health=FinancialHealth(
                status="No Data",
                savings_rate="0%",
                note="No transaction data available"
            ),
            statistical_insights=StatisticalInsights(
                income_spending_ratio=0,
                ratio_comment="No data available",
                top_category_concentration=0,
                concentration_comment="No data available",
                transaction_pattern="No data available",
                savings_assessment="No data available"
            ),
            metadata=InsightMetadata(
                total_transactions=0,
                analysis_period="No data",
                generated_at=datetime.now().isoformat(),
                model_used="none"
            )
        )
    
    async def generate_category_insights(self, 
                                       category: str,
                                       category_summary: CategorySummary) -> Dict[str, Any]:
        """
        Generate detailed insights for a specific category
        
        Args:
            category: Category name
            category_summary: Category summary data
            
        Returns:
            Category-specific insights
        """
        try:
            self.logger.info("Generating category insights", category=category)
            
            prompt = f"""
            Analyze the following spending category and provide detailed insights:
            
            CATEGORY: {category}
            Total Amount: ₹{category_summary.total_amount:,.2f}
            Transaction Count: {category_summary.transaction_count}
            Average Transaction: ₹{category_summary.average_amount:,.2f}
            Percentage of Total: {category_summary.percentage:.1f}%
            Largest Transaction: ₹{category_summary.largest_transaction:,.2f}
            
            RECENT TRANSACTIONS:
            {json.dumps([{
                "date": str(t.transaction_date),
                "description": t.description,
                "amount": t.amount
            } for t in category_summary.transactions[:5]], indent=2)}
            
            Please provide:
            1. Category-specific insights
            2. Spending patterns and trends
            3. Optimization recommendations
            4. Comparison with typical spending in this category
            
            Respond with JSON containing detailed analysis.
            """
            
            response = await self.arun(prompt)
            return self.parse_json_response(response.content)
            
        except Exception as e:
            return self.handle_error(e, f"generating insights for category {category}")
    
    async def detect_anomalies(self, transactions: List[CategorizedTransaction]) -> List[Dict[str, Any]]:
        """
        Detect spending anomalies and unusual patterns
        
        Args:
            transactions: List of categorized transactions
            
        Returns:
            List of detected anomalies
        """
        try:
            self.logger.info("Detecting spending anomalies", 
                           transaction_count=len(transactions))
            
            # Calculate basic statistics for anomaly detection
            amounts = [t.amount for t in transactions if t.type == 'debit']
            if not amounts:
                return []
            
            avg_amount = sum(amounts) / len(amounts)
            max_amount = max(amounts)
            
            # Prepare data for analysis
            transaction_data = []
            for t in transactions:
                transaction_data.append({
                    "date": str(t.transaction_date),
                    "description": t.description,
                    "amount": t.amount,
                    "category": t.category,
                    "type": t.type
                })
            
            prompt = f"""
            Analyze the following transactions and identify spending anomalies:
            
            SPENDING STATISTICS:
            Average Transaction: ₹{avg_amount:,.2f}
            Maximum Transaction: ₹{max_amount:,.2f}
            Total Transactions: {len(transactions)}
            
            TRANSACTIONS:
            {json.dumps(transaction_data, indent=2)}
            
            Please identify:
            1. Unusually large transactions (>3x average)
            2. Unexpected spending categories
            3. Recurring unusual patterns
            4. Potential duplicate transactions
            5. Suspicious transaction descriptions
            
            Respond with JSON containing anomaly details.
            """
            
            response = await self.arun(prompt)
            anomaly_result = self.parse_json_response(response.content)
            
            return anomaly_result.get("anomalies", [])
            
        except Exception as e:
            self.logger.error("Anomaly detection failed", error=str(e))
            return []
    
    async def predict_future_spending(self, 
                                    categorized_transactions: List[CategorizedTransaction],
                                    months_ahead: int = 3) -> Dict[str, Any]:
        """
        Predict future spending patterns based on historical data
        
        Args:
            categorized_transactions: Historical transaction data
            months_ahead: Number of months to predict
            
        Returns:
            Spending predictions
        """
        try:
            self.logger.info("Generating spending predictions", months_ahead=months_ahead)
            
            # Group transactions by category and month
            category_monthly_spending = {}
            
            for txn in categorized_transactions:
                if txn.type != 'debit':
                    continue
                
                category = txn.category
                # Extract month from transaction date
                month_key = str(txn.transaction_date)[:7] if isinstance(txn.transaction_date, str) else txn.transaction_date.strftime("%Y-%m")
                
                if category not in category_monthly_spending:
                    category_monthly_spending[category] = {}
                
                if month_key not in category_monthly_spending[category]:
                    category_monthly_spending[category][month_key] = 0
                
                category_monthly_spending[category][month_key] += txn.amount
            
            prompt = f"""
            Based on the following historical spending data, predict future spending:
            
            HISTORICAL SPENDING BY CATEGORY AND MONTH:
            {json.dumps(category_monthly_spending, indent=2)}
            
            Please predict spending for the next {months_ahead} months, considering:
            1. Historical trends
            2. Seasonal patterns
            3. Growth/decline patterns
            4. Category-specific behaviors
            
            Provide predictions with confidence levels and reasoning.
            Respond with JSON containing predictions.
            """
            
            response = await self.arun(prompt)
            return self.parse_json_response(response.content)
            
        except Exception as e:
            return self.handle_error(e, f"predicting spending for {months_ahead} months")
    
    def get_insights_stats(self) -> Dict[str, Any]:
        """
        Get insights agent statistics
        
        Returns:
            Statistics dictionary
        """
        base_stats = self.get_agent_stats()
        base_stats.update({
            "specialization": "Financial Insights & Analysis",
            "model_type": "gemini-flash (fast insights)",
            "capabilities": [
                "Comprehensive financial analysis",
                "Spending behavior insights",
                "Savings optimization",
                "Category-wise analysis",
                "Anomaly detection",
                "Future spending predictions",
                "Financial health assessment"
            ],
            "insight_types": [
                "Key insights",
                "Spending behavior",
                "Recommendations",
                "Financial health",
                "Statistical insights",
                "Category insights",
                "Trend analysis"
            ]
        })
        
        return base_stats