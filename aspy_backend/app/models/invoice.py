from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    amount = Column(Numeric(10, 2))
    currency = Column(String, default="USD")
    status = Column(String, default="pending")
    razorpay_order_id = Column(String, nullable=True)
    invoice_url = Column(String(500), nullable=True)  # Razorpay invoice download URL
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    paid_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="invoices")
    subscription = relationship("Subscription", back_populates="invoices")
    payment = relationship("Payment", back_populates="invoice")