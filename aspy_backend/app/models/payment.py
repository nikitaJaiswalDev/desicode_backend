from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import enum

class PaymentStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    amount = Column(Numeric(10, 2))
    currency = Column(String, default="USD")
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    
    # Provider details (Razorpay)
    provider = Column(String, default="razorpay")
    provider_payment_id = Column(String, unique=True, nullable=True)
    provider_order_id = Column(String, nullable=True)
    razorpay_invoice_id = Column(String, nullable=True)  # Razorpay invoice ID
    
    # Metadata like "Visa ending in 4242"
    payment_method_details = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")
    invoice = relationship("Invoice", uselist=False, back_populates="payment")
