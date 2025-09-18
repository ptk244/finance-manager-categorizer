from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum



class TransactionType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"

class SpendingCategory(str, Enum):
    FOOD_DINING = "Food & Dining"
    GROCERIES = "Groceries"
    TRANSPORTATION = "Transportation"
    ENTERTAINMENT = "Entertainment"
    UTILITIES = "Utilities"
    SHOPPING = "Shopping"
    HEALTHCARE = "Healthcare"
    EDUCATION = "Education"
    TRAVEL = "Travel"
    INVESTMENT = "Investment"
    SALARY = "Salary"
    BUSINESS = "Business"
    RENT_MORTGAGE = "Rent/Mortgage"
    INSURANCE = "Insurance"
    FUEL = "Fuel"
    ATM_CASH = "ATM/Cash"
    TRANSFER = "Transfer"
    FEES_CHARGES = "Fees & Charges"
    OTHER = "Other"

class Transaction(BaseModel):
    date: datetime
    description: str
    amount: float
    transaction_type: TransactionType
    balance: Optional[float] = None
    category: Optional[SpendingCategory] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    

class ProcessedBankStatement(BaseModel):
    file_name: str
    total_transactions: int
    date_range: Dict[str, datetime]
    total_debits: float
    total_credits: float
    current_balance: Optional[float] = None
    transactions: List[Transaction]

class CategorySummary(BaseModel):
    category: SpendingCategory
    total_amount: float
    transaction_count: int
    percentage: float
    avg_transaction: float

class InsightsSummary(BaseModel):
    total_expenses: float
    total_income: float
    net_savings: float
    top_category: CategorySummary
    largest_expense: Transaction
    category_breakdown: List[CategorySummary]
    insights_text: str
    recommendations: List[str]