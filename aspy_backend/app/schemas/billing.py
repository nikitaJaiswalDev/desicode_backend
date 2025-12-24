# app/schemas/billing.py
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime
from decimal import Decimal

class InvoiceResponse(BaseModel):
    id: int
    amount: Decimal
    currency: str
    status: str
    created_at: datetime
    paid_at: Optional[datetime]
    invoice_url: Optional[str] = None  # Razorpay invoice download URL

    class Config:
        from_attributes = True

class UsageStats(BaseModel):
    current_plan: str
    plan_type: str
    total_spent: float
    next_billing_date: Optional[datetime]
    usage_metrics: Dict[str, float]