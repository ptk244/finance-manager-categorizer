from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.response_models import InsightsResponse, VisualizationResponse, APIResponse
from services.agent_team_service import agent_team_service
from agents.insights_agent import insights_agent
from tools.visualization_tools import visualization_tools
from models.transaction import ProcessedBankStatement, Transaction
from typing import List, Optional, Dict, Any
from loguru import logger



router = APIRouter(prefix="/insights", tags=["Insights"])

class InsightsRequest(BaseModel):
    categorized_statement: dict  # ProcessedBankStatement as dict

class CategoryInsightsRequest(BaseModel):
    category: str
    transactions: List[dict]  # List of transactions for specific category

class VisualizationRequest(BaseModel):
    transactions: List[dict]
    category_data: Dict[str, float]
    chart_types: Optional[List[str]] = ["pie", "timeline", "bar", "comparison"]

@router.post("/generate", response_model=InsightsResponse)
async def generate_comprehensive_insights(request: InsightsRequest):
    """
    Generate comprehensive financial insights from categorized transactions
    
    Args:
        request: InsightsRequest with categorized statement data
    
    Returns:
        InsightsResponse with detailed financial insights
    """
    try:
        logger.info("Generating comprehensive financial insights")
        
        # Convert dict to ProcessedBankStatement object
        try:
            categorized_statement = ProcessedBankStatement(**request.categorized_statement)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid categorized statement format: {str(e)}"
            )
        
        # Generate insights
        insights_result = await insights_agent.generate_comprehensive_insights(categorized_statement)
        
        if not insights_result.get('success', False):
            raise HTTPException(
                status_code=400,
                detail=f"Insights generation failed: {insights_result.get('error', 'Unknown error')}"
            )
        
        return InsightsResponse(
            success=True,
            message="Comprehensive insights generated successfully",
            data=insights_result['insights_summary']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Insights generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Insights generation failed: {str(e)}")

@router.post("/category", response_model=APIResponse)
async def generate_category_insights(request: CategoryInsightsRequest):
    """
    Generate insights for a specific spending category
    
    Args:
        request: CategoryInsightsRequest with category and transactions
    
    Returns:
        APIResponse with category-specific insights
    """
    try:
        logger.info(f"Generating insights for category: {request.category}")
        
        # Convert transaction dicts to Transaction objects
        transaction_objects = []
        for trans_dict in request.transactions:
            try:
                transaction = Transaction(**trans_dict)
                transaction_objects.append(transaction)
            except Exception as e:
                logger.warning(f"Skipping invalid transaction: {str(e)}")
                continue
        
        if not transaction_objects:
            raise HTTPException(
                status_code=400,
                detail="No valid transactions found for the category"
            )
        
        # Generate category-specific insights
        category_insights_result = await insights_agent.generate_category_insights(
            request.category, 
            transaction_objects
        )
        
        if not category_insights_result.get('success', False):
            raise HTTPException(
                status_code=400,
                detail=f"Category insights generation failed: {category_insights_result.get('error', 'Unknown error')}"
            )
        
        return APIResponse(
            success=True,
            message=f"Category insights generated successfully for {request.category}",
            data=category_insights_result['category_insights']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Category insights generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Category insights failed: {str(e)}")

@router.post("/visualizations", response_model=VisualizationResponse)
async def create_visualizations(request: VisualizationRequest):
    """
    Create financial data visualizations
    
    Args:
        request: VisualizationRequest with transaction data and chart preferences
    
    Returns:
        VisualizationResponse with interactive charts and visualizations
    """
    try:
        logger.info("Creating financial visualizations")
        
        # Validate transaction data
        if not request.transactions:
            raise HTTPException(
                status_code=400,
                detail="No transaction data provided"
            )
        
        if not request.category_data:
            raise HTTPException(
                status_code=400,
                detail="No category data provided"
            )
        
        # Create visualizations based on requested chart types
        visualization_results = {}
        
        if "pie" in request.chart_types:
            pie_chart = visualization_tools.create_category_pie_chart(request.category_data)
            if 'error' not in pie_chart:
                visualization_results['pie_chart'] = pie_chart
        
        if "timeline" in request.chart_types:
            timeline_chart = visualization_tools.create_spending_timeline(request.transactions)
            if 'error' not in timeline_chart:
                visualization_results['timeline_chart'] = timeline_chart
        
        if "bar" in request.chart_types:
            bar_chart = visualization_tools.create_top_transactions_chart(request.transactions)
            if 'error' not in bar_chart:
                visualization_results['bar_chart'] = bar_chart
        
        if "comparison" in request.chart_types:
            comparison_chart = visualization_tools.create_category_comparison_chart(request.category_data)
            if 'error' not in comparison_chart:
                visualization_results['comparison_chart'] = comparison_chart
        
        # Always include income vs expense chart
        income_expense_chart = visualization_tools.create_income_vs_expense_chart(request.transactions)
        if 'error' not in income_expense_chart:
            visualization_results['income_expense_chart'] = income_expense_chart
        
        if not visualization_results:
            raise HTTPException(
                status_code=400,
                detail="Failed to create any visualizations"
            )
        
        return VisualizationResponse(
            success=True,
            message=f"Created {len(visualization_results)} visualizations successfully",
            data={
                "charts": visualization_results,
                "chart_count": len(visualization_results),
                "available_types": list(visualization_results.keys())
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Visualization creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Visualization creation failed: {str(e)}")

@router.post("/dashboard", response_model=VisualizationResponse)
async def create_comprehensive_dashboard(request: VisualizationRequest):
    """
    Create comprehensive financial dashboard with all visualizations
    
    Args:
        request: VisualizationRequest with transaction and category data
    
    Returns:
        VisualizationResponse with complete dashboard
    """
    try:
        logger.info("Creating comprehensive financial dashboard")
        
        # Validate data
        if not request.transactions or not request.category_data:
            raise HTTPException(
                status_code=400,
                detail="Both transaction and category data are required"
            )
        
        # Create comprehensive dashboard
        dashboard_result = visualization_tools.create_comprehensive_dashboard(
            request.transactions, 
            request.category_data
        )
        
        if 'error' in dashboard_result:
            raise HTTPException(
                status_code=400,
                detail=f"Dashboard creation failed: {dashboard_result['error']}"
            )
        
        return VisualizationResponse(
            success=True,
            message="Comprehensive dashboard created successfully",
            data=dashboard_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dashboard creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Dashboard creation failed: {str(e)}")

@router.get("/summary/spending", response_model=APIResponse)
async def get_spending_summary(transactions: List[dict]):
    """
    Get quick spending summary statistics
    
    Args:
        transactions: List of transaction dictionaries
    
    Returns:
        APIResponse with spending summary
    """
    try:
        logger.info("Generating spending summary")
        
        # Convert to Transaction objects
        transaction_objects = []
        for trans_dict in transactions:
            try:
                transaction = Transaction(**trans_dict)
                transaction_objects.append(transaction)
            except:
                continue
        
        if not transaction_objects:
            raise HTTPException(
                status_code=400,
                detail="No valid transactions provided"
            )
        
        # Calculate summary statistics
        total_expenses = sum(t.amount for t in transaction_objects if t.transaction_type.value == 'debit')
        total_income = sum(t.amount for t in transaction_objects if t.transaction_type.value == 'credit')
        net_savings = total_income - total_expenses
        
        expense_transactions = [t for t in transaction_objects if t.transaction_type.value == 'debit']
        income_transactions = [t for t in transaction_objects if t.transaction_type.value == 'credit']
        
        # Find largest transactions
        largest_expense = max(expense_transactions, key=lambda x: x.amount) if expense_transactions else None
        largest_income = max(income_transactions, key=lambda x: x.amount) if income_transactions else None
        
        # Category breakdown
        category_totals = {}
        for transaction in expense_transactions:
            if transaction.category:
                category = transaction.category.value
                category_totals[category] = category_totals.get(category, 0) + transaction.amount
        
        top_category = max(category_totals, key=category_totals.get) if category_totals else None
        
        summary_data = {
            "total_transactions": len(transaction_objects),
            "total_expenses": round(total_expenses, 2),
            "total_income": round(total_income, 2),
            "net_savings": round(net_savings, 2),
            "expense_transaction_count": len(expense_transactions),
            "income_transaction_count": len(income_transactions),
            "largest_expense": {
                "amount": largest_expense.amount,
                "description": largest_expense.description,
                "date": largest_expense.date.strftime('%Y-%m-%d')
            } if largest_expense else None,
            "largest_income": {
                "amount": largest_income.amount,
                "description": largest_income.description,
                "date": largest_income.date.strftime('%Y-%m-%d')
            } if largest_income else None,
            "top_spending_category": {
                "category": top_category,
                "amount": category_totals.get(top_category, 0),
                "percentage": round((category_totals.get(top_category, 0) / total_expenses) * 100, 1) if total_expenses > 0 else 0
            } if top_category else None,
            "savings_rate": round((net_savings / total_income) * 100, 1) if total_income > 0 else 0,
            "average_expense": round(total_expenses / len(expense_transactions), 2) if expense_transactions else 0,
            "average_income": round(total_income / len(income_transactions), 2) if income_transactions else 0
        }
        
        return APIResponse(
            success=True,
            message="Spending summary generated successfully",
            data=summary_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Spending summary generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Spending summary failed: {str(e)}")

@router.get("/recommendations", response_model=APIResponse)
async def get_financial_recommendations():
    """
    Get general financial management recommendations
    
    Returns:
        APIResponse with financial recommendations
    """
    try:
        recommendations = {
            "budgeting": [
                "Follow the 50-30-20 rule: 50% needs, 30% wants, 20% savings",
                "Track your expenses regularly to identify spending patterns",
                "Set up automatic transfers to savings accounts",
                "Review and adjust your budget monthly"
            ],
            "spending_optimization": [
                "Identify and reduce unnecessary subscription services",
                "Compare prices before making large purchases",
                "Use cashback and reward programs effectively",
                "Plan meals to reduce food waste and dining out costs"
            ],
            "savings_strategies": [
                "Build an emergency fund covering 3-6 months of expenses",
                "Take advantage of employer matching in retirement accounts",
                "Consider systematic investment plans (SIPs) for long-term goals",
                "Automate your savings to pay yourself first"
            ],
            "investment_tips": [
                "Diversify your investment portfolio across asset classes",
                "Start investing early to benefit from compound interest",
                "Review and rebalance your portfolio annually",
                "Consider tax-saving investment options like ELSS funds"
            ],
            "debt_management": [
                "Pay off high-interest debt first (debt avalanche method)",
                "Consider debt consolidation for multiple loans",
                "Avoid minimum payments on credit cards",
                "Negotiate with creditors for better terms when possible"
            ]
        }
        
        return APIResponse(
            success=True,
            message="Financial recommendations retrieved successfully",
            data=recommendations
        )
        
    except Exception as e:
        logger.error(f"Failed to get recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")

@router.post("/alerts", response_model=APIResponse)
async def generate_spending_alerts(transactions: List[dict], thresholds: Optional[Dict[str, float]] = None):
    """
    Generate spending alerts based on transaction patterns and thresholds
    
    Args:
        transactions: List of transaction dictionaries
        thresholds: Optional spending thresholds for different categories
    
    Returns:
        APIResponse with spending alerts and warnings
    """
    try:
        logger.info("Generating spending alerts")
        
        # Default thresholds (in INR)
        default_thresholds = {
            "Food & Dining": 10000,
            "Entertainment": 5000,
            "Shopping": 15000,
            "Transportation": 8000,
            "Utilities": 5000
        }
        
        if thresholds:
            default_thresholds.update(thresholds)
        
        # Convert to Transaction objects
        transaction_objects = []
        for trans_dict in transactions:
            try:
                transaction = Transaction(**trans_dict)
                transaction_objects.append(transaction)
            except:
                continue
        
        alerts = []
        warnings = []
        
        # Category-wise spending analysis
        category_spending = {}
        for transaction in transaction_objects:
            if transaction.transaction_type.value == 'debit' and transaction.category:
                category = transaction.category.value
                category_spending[category] = category_spending.get(category, 0) + transaction.amount
        
        # Check thresholds
        for category, spent_amount in category_spending.items():
            threshold = default_thresholds.get(category)
            if threshold and spent_amount > threshold:
                alerts.append({
                    "type": "overspending",
                    "category": category,
                    "spent_amount": spent_amount,
                    "threshold": threshold,
                    "excess_amount": spent_amount - threshold,
                    "message": f"You've exceeded your {category} budget by ₹{spent_amount - threshold:.2f}"
                })
            elif threshold and spent_amount > threshold * 0.8:
                warnings.append({
                    "type": "approaching_limit",
                    "category": category,
                    "spent_amount": spent_amount,
                    "threshold": threshold,
                    "percentage": (spent_amount / threshold) * 100,
                    "message": f"You're approaching your {category} budget limit ({(spent_amount / threshold) * 100:.1f}%)"
                })
        
        # Large transaction alerts
        expense_amounts = [t.amount for t in transaction_objects if t.transaction_type.value == 'debit']
        if expense_amounts:
            avg_expense = sum(expense_amounts) / len(expense_amounts)
            large_transactions = [t for t in transaction_objects 
                                if t.transaction_type.value == 'debit' and t.amount > avg_expense * 3]
            
            for transaction in large_transactions:
                alerts.append({
                    "type": "large_transaction",
                    "transaction": {
                        "description": transaction.description,
                        "amount": transaction.amount,
                        "date": transaction.date.strftime('%Y-%m-%d')
                    },
                    "average_expense": avg_expense,
                    "message": f"Large expense detected: ₹{transaction.amount:.2f} at {transaction.description}"
                })
        
        return APIResponse(
            success=True,
            message=f"Generated {len(alerts)} alerts and {len(warnings)} warnings",
            data={
                "alerts": alerts,
                "warnings": warnings,
                "alert_count": len(alerts),
                "warning_count": len(warnings),
                "thresholds_used": default_thresholds
            }
        )
        
    except Exception as e:
        logger.error(f"Alert generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Alert generation failed: {str(e)}")