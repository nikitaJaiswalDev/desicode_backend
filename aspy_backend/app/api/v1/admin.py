from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User, UserType
from app.models.subscription import Subscription, Plan, SubscriptionStatus
from app.models.invoice import Invoice
from app.models.language import Language
from app.models.code_execution import CodeExecution
from app.models.payment import Payment, PaymentStatus
from pydantic import BaseModel, EmailStr
from datetime import datetime

router = APIRouter()

# Dependency to check if user is admin
def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized. Admin access required."
        )
    return current_user

# Schemas
class UserAdminResponse(BaseModel):
    id: int
    username: str
    email: str
    user_type: str
    is_active: bool
    created_at: datetime
    subscription_status: Optional[str] = None
    subscription_plan: Optional[str] = None
    execution_count: int = 0
    certificate_count: int = 0

    class Config:
        from_attributes = True

class SubscriptionAdminResponse(BaseModel):
    id: int
    user_email: str
    plan_name: str
    status: str
    amount_paid: float
    next_due_date: Optional[datetime] = None
    created_at: datetime
    current_period_end: Optional[datetime] = None

    class Config:
        from_attributes = True

class LanguageResponse(BaseModel):
    id: int
    name: str
    slug: str

    class Config:
        from_attributes = True

class LanguageCreate(BaseModel):
    name: str
    slug: str

class DashboardStats(BaseModel):
    total_users: int
    total_admins: int
    active_subscriptions: int
    total_revenue: float
    total_executions: int
    total_languages: int

# Admin Endpoints

@router.get("/admin/stats", response_model=DashboardStats, tags=["Admin"])
def get_admin_dashboard_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get admin dashboard statistics"""
    total_users = db.query(User).filter(User.user_type == UserType.USER).count()
    total_admins = db.query(User).filter(User.user_type == UserType.ADMIN).count()
    active_subscriptions = db.query(Subscription).filter(Subscription.status == SubscriptionStatus.ACTIVE).count()
    
    # Calculate total revenue from completed payments
    total_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.status == PaymentStatus.COMPLETED
    ).scalar() or 0.0
    
    total_executions = db.query(CodeExecution).count()
    total_languages = db.query(Language).count()
    
    return {
        "total_users": total_users,
        "total_admins": total_admins,
        "active_subscriptions": active_subscriptions,
        "total_revenue": float(total_revenue),
        "total_executions": total_executions,
        "total_languages": total_languages
    }

@router.get("/admin/users", response_model=List[UserAdminResponse], tags=["Admin"])
def get_all_users(
    search: Optional[str] = Query(None, description="Search by name or email"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get all users with their subscription and execution details"""
    query = db.query(User).filter(User.user_type == UserType.USER)
    
    # Apply search filter
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                User.username.ilike(search_filter),
                User.email.ilike(search_filter)
            )
        )
    
    users = query.offset(skip).limit(limit).all()
    
    response = []
    for user in users:
        # Get user's active subscription
        active_subscription = db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE
        ).first()
        
        # Get execution count
        execution_count = db.query(CodeExecution).filter(
            CodeExecution.user_id == user.id
        ).count()
        
        # For now, certificate count is 0 (implement later if you have certificates table)
        certificate_count = 0
        
        response.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "user_type": user.user_type.value,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "subscription_status": active_subscription.status.value if active_subscription else None,
            "subscription_plan": active_subscription.plan.name if active_subscription and active_subscription.plan else None,
            "execution_count": execution_count,
            "certificate_count": certificate_count
        })
    
    return response

@router.get("/admin/subscriptions", response_model=List[SubscriptionAdminResponse], tags=["Admin"])
def get_all_subscriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get all subscriptions with user and payment details"""
    subscriptions = db.query(Subscription).offset(skip).limit(limit).all()
    
    response = []
    for sub in subscriptions:
        # Get the latest completed payment for this user
        latest_payment = db.query(Payment).filter(
            Payment.user_id == sub.user_id,
            Payment.status == PaymentStatus.COMPLETED
        ).order_by(Payment.created_at.desc()).first()
        
        amount_paid = latest_payment.amount if latest_payment else 0.0
        
        response.append({
            "id": sub.id,
            "user_email": sub.user.email if sub.user else "N/A",
            "plan_name": sub.plan.name if sub.plan else "N/A",
            "status": sub.status.value if hasattr(sub.status, 'value') else str(sub.status),
            "amount_paid": float(amount_paid),
            "next_due_date": sub.current_period_end,
            "created_at": sub.created_at,
            "current_period_end": sub.current_period_end
        })
    
    return response

@router.get("/admin/languages", response_model=List[LanguageResponse], tags=["Admin"])
def get_all_languages(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get all supported languages"""
    languages = db.query(Language).all()
    return languages

@router.post("/admin/languages", response_model=LanguageResponse, status_code=status.HTTP_201_CREATED, tags=["Admin"])
def create_language(
    language: LanguageCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Create a new language"""
    # Check if language already exists
    existing = db.query(Language).filter(
        or_(
            Language.name == language.name,
            Language.slug == language.slug
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Language with this name or slug already exists"
        )
    
    new_language = Language(
        name=language.name,
        slug=language.slug
    )
    
    db.add(new_language)
    db.commit()
    db.refresh(new_language)
    
    return new_language

@router.delete("/admin/languages/{language_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Admin"])
def delete_language(
    language_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Delete a language"""
    language = db.query(Language).filter(Language.id == language_id).first()
    
    if not language:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Language not found"
        )
    
    db.delete(language)
    db.commit()
    
    return None

@router.patch("/admin/users/{user_id}/toggle-status", tags=["Admin"])
def toggle_user_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Toggle user active status"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.user_type == UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify admin user status"
        )
    
    user.is_active = not user.is_active
    db.commit()
    
    return {
        "message": f"User {'activated' if user.is_active else 'deactivated'} successfully",
        "user_id": user.id,
        "is_active": user.is_active
    }

@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Admin"])
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Delete a user"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.user_type == UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete admin user"
        )
    
    db.delete(user)
    db.commit()
    
    return None
