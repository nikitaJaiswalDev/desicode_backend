from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
from sqlalchemy import JSON
import enum

class PlanType(enum.Enum):
    FREE = "free"
    PRO = "pro"

class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    type = Column(SQLEnum(PlanType), unique=True)
    price = Column(Integer)
    currency = Column(String, default="USD")
    features = Column(JSON) # Changed to JSON type
    razorpay_plan_id = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    subscriptions = relationship("Subscription", back_populates="plan")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan_id = Column(Integer, ForeignKey("plans.id"))
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    razorpay_subscription_id = Column(String, nullable=True, unique=True)
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    cancelled_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription")
    payments = relationship("Payment", back_populates="subscription")