"""
Transaction data models
"""
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class Transaction(BaseModel):
    """Base transaction model"""
    transaction_date: date | str = Field(..., description="Transaction date")
    description: str = Field(..., description="Transaction description/narration")
    amount: float = Field(..., description="Transaction amount")
    type: str = Field(..., description="Transaction type (debit/credit)")
    balance: Optional[float] = Field(None, description="Account balance after transaction")
    reference: Optional[str] = Field(None, description="Transaction reference number")

    # ✅ use field_validator instead of old validator
    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate transaction type"""
        if v.lower() not in ["debit", "credit"]:
            raise ValueError("Transaction type must be either debit or credit")
        return v.lower()

    @field_validator("transaction_date", mode="before")
    @classmethod
    def parse_date(cls, v):
        """Parse various date formats"""
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            date_formats = [
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%d-%m-%Y",
                "%m/%d/%Y",
                "%d.%m.%Y",
                "%Y-%m-%d %H:%M:%S",
                "%d/%m/%Y %H:%M:%S",
            ]
            for fmt in date_formats:
                try:
                    return datetime.strptime(v, fmt).date()
                except ValueError:
                    continue
            return v  # fallback to string
        return v


class CategorizedTransaction(Transaction):
    """Transaction with categorization information"""
    category: str = Field(..., description="Primary category")
    subcategory: Optional[str] = Field(None, description="Subcategory")
    confidence: float = Field(..., description="Categorization confidence (0-1)")
    reasoning: Optional[str] = Field(None, description="AI reasoning for categorization")

    # Additional computed fields
    amount_inr: float = Field(..., description="Amount in INR")
    debited_amount_inr: float = Field(0.0, description="Debited amount in INR")
    credited_amount_inr: float = Field(0.0, description="Credited amount in INR")
    current_balance_inr: Optional[float] = Field(None, description="Current balance in INR")

    def __init__(self, **data):
        super().__init__(**data)
        # Auto-calculate INR amounts
        self.amount_inr = self.amount
        if self.type == "debit":
            self.debited_amount_inr = self.amount
            self.credited_amount_inr = 0.0
        else:
            self.debited_amount_inr = 0.0
            self.credited_amount_inr = self.amount
        if self.balance is not None:
            self.current_balance_inr = self.balance


class TransactionBatch(BaseModel):
    """Batch of transactions for processing"""
    transactions: list[Transaction] = Field(..., description="List of transactions")
    total_count: int = Field(..., description="Total number of transactions")
    file_name: Optional[str] = Field(None, description="Source file name")
    processing_metadata: Optional[dict] = Field(None, description="Processing metadata")

    @field_validator("total_count")
    @classmethod
    def validate_count(cls, v, values):
        """Validate transaction count matches list length"""
        if "transactions" in values and len(values["transactions"]) != v:
            raise ValueError("Total count must match transactions list length")
        return v


class CategorizationRules(BaseModel):
    """User-defined categorization rules"""
    pattern: str = Field(..., description="Description pattern to match")
    category: str = Field(..., description="Target category")
    subcategory: Optional[str] = Field(None, description="Target subcategory")
    confidence: float = Field(1.0, description="Rule confidence")
    user_defined: bool = Field(True, description="Whether rule is user-defined")
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        }
    }
