"""
Financial insights data models
"""
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from .transaction import CategorizedTransaction


class CategorySummary(BaseModel):
    """Summary statistics for a transaction category"""
    total_amount: float = Field(..., description="Total amount for this category")
    transaction_count: int = Field(..., description="Number of transactions")
    percentage: float = Field(..., description="Percentage of total spending")
    transactions: List[CategorizedTransaction] = Field(..., description="List of transactions in this category")
    average_amount: Optional[float] = Field(None, description="Average transaction amount")
    largest_transaction: Optional[float] = Field(None, description="Largest single transaction")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Calculate derived fields
        if self.transactions:
            amounts = [t.amount for t in self.transactions]
            self.average_amount = sum(amounts) / len(amounts)
            self.largest_transaction = max(amounts)


class SpendingBehavior(BaseModel):
    """Analysis of spending behavior patterns"""
    total_spending: float = Field(..., description="Total spending amount")
    total_income: float = Field(..., description="Total income amount")
    net_savings: float = Field(..., description="Net savings (income - spending)")
    transaction_count: int = Field(..., description="Total number of transactions")
    savings_rate: Optional[float] = Field(None, description="Savings rate percentage")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Calculate savings rate
        if self.total_income > 0:
            self.savings_rate = (self.net_savings / self.total_income) * 100


class FinancialHealth(BaseModel):
    """Financial health assessment"""
    status: str = Field(..., description="Overall financial health status")
    savings_rate: str = Field(..., description="Savings rate as string")
    note: str = Field(..., description="Health assessment note")
    score: Optional[float] = Field(None, description="Numeric health score (0-100)")


class StatisticalInsights(BaseModel):
    """Statistical analysis of financial data"""
    income_spending_ratio: float = Field(..., description="Ratio of spending to income")
    ratio_comment: str = Field(..., description="Comment on the ratio")
    top_category_concentration: float = Field(..., description="Concentration in top spending category")
    concentration_comment: str = Field(..., description="Comment on spending concentration")
    transaction_pattern: str = Field(..., description="Description of transaction patterns")
    savings_assessment: str = Field(..., description="Assessment of savings behavior")


class InsightMetadata(BaseModel):
    """Metadata for insight generation"""
    total_transactions: int = Field(..., description="Total number of transactions analyzed")
    analysis_period: str = Field(..., description="Period covered by analysis")
    generated_at: str = Field(..., description="Timestamp when insights were generated")
    model_used: Optional[str] = Field(None, description="AI model used for insights")


class FinancialInsights(BaseModel):
    """Complete financial insights package"""
    key_insights: List[str] = Field(..., description="List of key insights")
    spending_behavior: SpendingBehavior = Field(..., description="Spending behavior analysis")
    recommendations: List[str] = Field(..., description="AI-generated recommendations")
    financial_health: FinancialHealth = Field(..., description="Financial health assessment")
    statistical_insights: StatisticalInsights = Field(..., description="Statistical analysis")
    metadata: InsightMetadata = Field(..., description="Generation metadata")
    
    # Optional advanced insights
    monthly_trends: Optional[Dict[str, Any]] = Field(None, description="Monthly trend analysis")
    category_insights: Optional[Dict[str, Any]] = Field(None, description="Category-specific insights")
    anomalies: Optional[List[Dict[str, Any]]] = Field(None, description="Detected anomalies")


class InsightRequest(BaseModel):
    """Request model for insight generation"""
    include_trends: bool = Field(True, description="Include trend analysis")
    include_predictions: bool = Field(False, description="Include future predictions")
    focus_categories: Optional[List[str]] = Field(None, description="Categories to focus analysis on")
    time_period: Optional[str] = Field(None, description="Specific time period to analyze")


class CategoryInsight(BaseModel):
    """Detailed insights for a specific category"""
    category: str = Field(..., description="Category name")
    total_spent: float = Field(..., description="Total amount spent in category")
    transaction_frequency: int = Field(..., description="Number of transactions")
    average_transaction: float = Field(..., description="Average transaction amount")
    trend: str = Field(..., description="Spending trend (increasing/decreasing/stable)")
    insights: List[str] = Field(..., description="Category-specific insights")
    recommendations: List[str] = Field(..., description="Category-specific recommendations")


class TrendAnalysis(BaseModel):
    """Trend analysis data"""
    period: str = Field(..., description="Analysis period")
    trend_direction: str = Field(..., description="Overall trend direction")
    growth_rate: Optional[float] = Field(None, description="Growth rate percentage")
    seasonal_patterns: Optional[Dict[str, Any]] = Field(None, description="Seasonal patterns detected")
    notable_changes: List[str] = Field(..., description="Notable changes identified")