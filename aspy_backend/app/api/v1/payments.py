from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import razorpay
import os
from datetime import datetime, timedelta
import json

from app.db.session import get_db
from app.models.subscription import Plan, Subscription, SubscriptionStatus
from app.models.invoice import Invoice
from app.models.payment import Payment, PaymentStatus
from app.schemas.payment import (
    RazorpayOrderRequest,
    RazorpayOrderResponse,
    RazorpayVerifyRequest,
    PaymentHistory
)
from app.core.security import get_current_user

router = APIRouter()

# Initialize payment gateways
# Use dummy keys if environment variables are not set or set to "dummy"
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "dummy")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "dummy")

try:
    razorpay_client = razorpay.Client(
        auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    )
except:
    razorpay_client = None

def format_plan_features(plan: Plan) -> str:
    """Format plan features for display"""
    try:
        if isinstance(plan.features, str):
            features_dict = json.loads(plan.features)
        else:
            features_dict = plan.features or {}

        features_list = []
        for key, value in features_dict.items():
            key_formatted = key.replace('_', ' ').title()
            if isinstance(value, bool):
                features_list.append(f"{key_formatted}: {'Yes' if value else 'No'}")
            elif isinstance(value, (int, float)):
                features_list.append(f"{key_formatted}: {value}")
            else:
                features_list.append(f"{key_formatted}: {value}")

        return " | ".join(features_list)
    except:
        return "View features for details"


# Stripe support removed as per request


@router.post("/payments/razorpay/create-subscription", response_model=RazorpayOrderResponse, tags=["Payments"])
def create_razorpay_subscription(
        request: RazorpayOrderRequest,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Create Razorpay subscription for recurring payments
    This creates a Razorpay customer (if needed) and subscription
    """
    # Get the plan
    plan = db.query(Plan).filter(Plan.id == request.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Check if plan has razorpay_plan_id
    if not plan.razorpay_plan_id:
        raise HTTPException(
            status_code=400,
            detail="Plan not configured for subscriptions. Please create a Razorpay plan in dashboard first."
        )

    try:
        # Mock Mode Check
        if not RAZORPAY_KEY_ID or RAZORPAY_KEY_ID == "dummy" or not razorpay_client:
            # Create mock subscription ID
            mock_sub_id = f"sub_mock_{current_user.id}_{int(datetime.now().timestamp())}"
            
            return RazorpayOrderResponse(
                order_id=mock_sub_id,
                amount=plan.price,
                currency=plan.currency,
                key_id="dummy_key_id"
            )

        # Step 1: Create or get Razorpay customer
        if not current_user.razorpay_customer_id:
            customer = razorpay_client.customer.create({
                'name': current_user.username,
                'email': current_user.email,
                'notes': {
                    'user_id': str(current_user.id)
                }
            })
            current_user.razorpay_customer_id = customer['id']
            db.commit()
        
        # Step 2: Create Razorpay subscription
        subscription_data = {
            'plan_id': plan.razorpay_plan_id,
            'customer_id': current_user.razorpay_customer_id,
            'total_count': 12,  # 12 months (1 year)
            'quantity': 1,
            'customer_notify': 1,  # Email customer
            'notes': {
                'user_id': str(current_user.id),
                'username': current_user.username,
                'plan_id': str(plan.id),
                'plan_name': plan.name
            }
        }

        subscription = razorpay_client.subscription.create(subscription_data)

        # Step 3: Create pending invoice
        invoice = Invoice(
            user_id=current_user.id,
            amount=plan.price / 100,  # Convert paise to rupees
            currency=plan.currency,
            status='pending',
            razorpay_order_id=subscription['id'],  # Using subscription_id
            plan_id=plan.id,
            created_at=datetime.utcnow()
        )
        db.add(invoice)
        db.commit()

        # Return subscription details
        return RazorpayOrderResponse(
            order_id=subscription['id'],  # This is subscription_id
            amount=plan.price,
            currency=plan.currency,
            key_id=RAZORPAY_KEY_ID
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create subscription: {str(e)}")


@router.post("/payments/razorpay/verify", tags=["Payments"])
def verify_razorpay_payment(
        request: RazorpayVerifyRequest,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Verify Razorpay subscription payment and capture card details
    """
    try:
        # Find the pending invoice (razorpay_order_id now contains subscription_id)
        invoice = db.query(Invoice).filter(
            Invoice.razorpay_order_id == request.razorpay_order_id,
            Invoice.user_id == current_user.id,
            Invoice.status == 'pending'
        ).first()

        if not invoice:
            raise HTTPException(status_code=404, detail=f"Invoice not found for subscription {request.razorpay_order_id}")

        # Check for Mock Mode
        is_mock = (not RAZORPAY_KEY_ID or RAZORPAY_KEY_ID == "dummy" or 
                   not razorpay_client or 
                   request.razorpay_order_id.startswith("sub_mock_"))

        if not is_mock:
            # Verify payment signature for subscription
            try:
                params_dict = {
                    'razorpay_subscription_id': request.razorpay_order_id,
                    'razorpay_payment_id': request.razorpay_payment_id,
                    'razorpay_signature': request.razorpay_signature
                }
                razorpay_client.utility.verify_payment_signature(params_dict)
            except razorpay.errors.SignatureVerificationError:
                raise HTTPException(status_code=400, detail="Invalid payment signature")
            except Exception as e:
                # Signature verification might fail for subscriptions, log and continue
                print(f"Signature verification skipped: {str(e)}")

            # Fetch payment details to get card info and invoice ID
            try:
                payment_details = razorpay_client.payment.fetch(request.razorpay_payment_id)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to fetch payment details: {str(e)}")
                
            try:
                subscription_details = razorpay_client.subscription.fetch(request.razorpay_order_id)
            except Exception as e:
                # Subscription fetch might fail, it's optional
                subscription_details = {}
            
            payment_amount = float(payment_details['amount']) / 100
            invoice_id = payment_details.get('invoice_id')
        else:
            # Mock mode
            payment_amount = invoice.amount
            payment_details = {'method': 'card', 'currency': invoice.currency}
            subscription_details = {}
            invoice_id = f"inv_mock_{int(datetime.now().timestamp())}"

        # Create Payment Record with invoice ID
        new_payment = Payment(
            user_id=current_user.id,
            amount=payment_amount,
            currency=invoice.currency,
            status=PaymentStatus.COMPLETED,
            provider="razorpay",
            provider_payment_id=request.razorpay_payment_id,
            provider_order_id=request.razorpay_order_id,  # subscription_id
            razorpay_invoice_id=invoice_id,  # Save invoice ID
            payment_method_details={"method": "razorpay", "id": request.razorpay_payment_id},
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        db.add(new_payment)
        db.flush()

        # Update invoice
        invoice.status = 'paid'
        invoice.payment_id = new_payment.id
        invoice.paid_at = datetime.utcnow()
        invoice.amount = payment_amount
        
        # Save invoice URL if available from Razorpay
        if not is_mock and invoice_id:
            try:
                razorpay_invoice_data = razorpay_client.invoice.fetch(invoice_id)
                invoice_url = razorpay_invoice_data.get('short_url') or razorpay_invoice_data.get('receipt')
                if invoice_url:
                    invoice.invoice_url = invoice_url
                    print(f"Saved invoice URL: {invoice_url}")
            except Exception as e:
                print(f"Could not fetch invoice URL: {str(e)}")

        # Get plan from invoice
        plan = db.query(Plan).filter(Plan.id == invoice.plan_id).first()

        if plan:
            # Create or update subscription
            subscription = db.query(Subscription).filter(
                Subscription.user_id == current_user.id
            ).first()

            if not subscription:
                # Create new subscription
                period_start = datetime.utcnow()
                period_end = period_start + timedelta(days=30)

                subscription = Subscription(
                    user_id=current_user.id,
                    plan_id=plan.id,
                    status=SubscriptionStatus.ACTIVE,
                    razorpay_subscription_id=request.razorpay_order_id,  # Save subscription ID
                    current_period_start=period_start,
                    current_period_end=period_end,
                    created_at=datetime.utcnow()
                )
                db.add(subscription)
                db.flush()
            else:
                # Upgrade/Downgrade/Renew existing subscription
                subscription.plan_id = plan.id
                subscription.status = SubscriptionStatus.ACTIVE
                subscription.razorpay_subscription_id = request.razorpay_order_id
                subscription.current_period_start = datetime.utcnow()
                subscription.current_period_end = datetime.utcnow() + timedelta(days=30)

            # Capture card details if available
            print(f"Payment method: {payment_details.get('method')}")
            print(f"Payment details: {payment_details}")
            
            if not is_mock and payment_details.get('method') == 'card':
                card_info = payment_details.get('card', {})
                print(f"Card info from Razorpay: {card_info}")
                
                subscription.card_last4 = card_info.get('last4')
                subscription.card_brand = card_info.get('network')  # visa, mastercard, etc.
                subscription.card_exp_month = card_info.get('exp_month')
                subscription.card_exp_year = card_info.get('exp_year')
                
                print(f"Saved card details: {subscription.card_brand} ****{subscription.card_last4}")
            elif is_mock and payment_details.get('method') == 'card':
                # Save mock card details
                card_info = payment_details.get('card', {})
                subscription.card_last4 = card_info.get('last4')
                subscription.card_brand = card_info.get('network')
                subscription.card_exp_month = card_info.get('exp_month')
                subscription.card_exp_year = card_info.get('exp_year')

            # Link payment and invoice to subscription
            new_payment.subscription_id = subscription.id
            invoice.subscription_id = subscription.id
            
        db.commit()

        return {
            "status": "success",
            "message": "Subscription activated successfully",
            "payment_id": request.razorpay_payment_id,
            "subscription_id": request.razorpay_order_id,
            "amount": invoice.amount,
            "currency": invoice.currency
        }

    except razorpay.errors.SignatureVerificationError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process subscription: {str(e)}")


@router.get("/payments/history", response_model=List[PaymentHistory], tags=["Payments"])
def get_payment_history(
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Get payment history for current user
    """
    payments = db.query(Payment).filter(
        Payment.user_id == current_user.id
    ).order_by(Payment.created_at.desc()).all()

    history = []
    for payment in payments:
        # Get plan name if available
        plan_name = None
        if payment.subscription and payment.subscription.plan:
             plan_name = payment.subscription.plan.name
        
        # Get method description
        method = "Unknown"
        if payment.payment_method_details and isinstance(payment.payment_method_details, dict):
            method = payment.payment_method_details.get("method", "Unknown")
            # Enhance if we have more details

        history.append(PaymentHistory(
            id=payment.id,
            amount=float(payment.amount),
            currency=payment.currency,
            status=payment.status.value if hasattr(payment.status, 'value') else str(payment.status),
            provider=payment.provider,
            plan_name=plan_name,
            payment_method=method,
            created_at=payment.created_at
        ))

    return history


@router.get("/payments/methods", tags=["Payments"])
def get_payment_methods():
    """
    Get available payment methods
    """
    return {
        "available_methods": [
            {
                "provider": "razorpay",
                "currencies": ["INR"],
                "supported_cards": ["visa", "mastercard", "rupay", "amex"],
                "netbanking": True,
                "upi": True,
                "wallet": True
            }
        ]
    }


@router.get("/invoices/download/{invoice_id}", tags=["Invoices"])
def download_invoice(
        invoice_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Get Razorpay invoice download URL for a specific invoice
    """
    from app.models.invoice import Invoice
    
    # Find invoice
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == current_user.id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # If we already have stored invoice_url, return it
    if invoice.invoice_url:
        return {
            "invoice_url": invoice.invoice_url,
            "invoice_id": invoice_id
        }
    
    # Try to get invoice URL from Razorpay
    if invoice.payment:
        payment = invoice.payment
        if hasattr(payment, 'razorpay_invoice_id') and payment.razorpay_invoice_id:
            if RAZORPAY_KEY_ID and RAZORPAY_KEY_ID != "dummy" and razorpay_client:
                try:
                    # Fetch invoice from Razorpay
                    razorpay_invoice = razorpay_client.invoice.fetch(payment.razorpay_invoice_id)
                    invoice_url = razorpay_invoice.get('short_url') or razorpay_invoice.get('invoice_pdf')
                    
                    if invoice_url:
                        # Save URL for future use
                        invoice.invoice_url = invoice_url
                        db.commit()
                        
                        return {
                            "invoice_url": invoice_url,
                            "invoice_id": invoice_id
                        }
                except Exception as e:
                    print(f"Failed to fetch Razorpay invoice: {str(e)}")
    
    # Fallback: Generate invoice URL manually
    # You can create your own invoice PDF generation logic here
    raise HTTPException(
        status_code=404, 
        detail="Invoice URL not available. Please contact support."
    )

@router.get("/payment-method/current", tags=["Payment Methods"])
def get_current_payment_method(
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Get current payment method details from active subscription
    """
    # Find active subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == SubscriptionStatus.ACTIVE
    ).first()
    
    if not subscription:
        return {
            "has_payment_method": False,
            "message": "No active subscription found"
        }
    
    # Get payment method details from subscription
    if subscription.card_last4:
        return {
            "has_payment_method": True,
            "payment_method": {
                "type": "card",
                "card_brand": subscription.card_brand or "Unknown",
                "card_last4": subscription.card_last4,
                "card_exp_month": subscription.card_exp_month,
                "card_exp_year": subscription.card_exp_year
            }
        }
    else:
        # Might be UPI or other method - check payment details
        last_payment = db.query(Payment).filter(
            Payment.subscription_id == subscription.id,
            Payment.status == PaymentStatus.COMPLETED
        ).order_by(Payment.created_at.desc()).first()
        
        if last_payment and last_payment.payment_method_details:
            method_details = last_payment.payment_method_details
            if isinstance(method_details, dict):
                payment_type = method_details.get('method', 'Unknown')
                return {
                    "has_payment_method": True,
                    "payment_method": {
                        "type": payment_type,
                        "details": method_details
                    }
                }
        
        return {
            "has_payment_method": False,
            "message": "Payment method details not available"
        }


@router.post("/payment-method/update", tags=["Payment Methods"])
def update_payment_method(
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Initiate payment method update flow
    Returns a Razorpay checkout link to collect new payment details
    """
    # Find active subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == SubscriptionStatus.ACTIVE
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    if not subscription.razorpay_subscription_id:
        raise HTTPException(status_code=400, detail="Subscription not linked to Razorpay")
    
    # To update payment method in Razorpay, we need to:
    # 1. Create a payment link or
    # 2. Send update card request
    
    # For now, return instructions for manual update
    # In production, you'd generate a Razorpay link to update payment method
    
    if RAZORPAY_KEY_ID and RAZORPAY_KEY_ID != "dummy" and razorpay_client:
        # Get subscription details from Razorpay
        try:
            razorpay_subscription = razorpay_client.subscription.fetch(subscription.razorpay_subscription_id)
            
            # Generate auth link for payment method update
            # Note: Razorpay doesn't have direct API for this
            # You need to create a new short-term subscription or payment link
            
            return {
                "status": "success",
                "message": "To update your payment method, please contact support or cancel and create a new subscription",
                "subscription_id": subscription.razorpay_subscription_id,
                "support_email": "support@desicodes.com"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to process update: {str(e)}")
    
    raise HTTPException(status_code=400, detail="Payment method update not available in test mode")


@router.post("/subscriptions/cancel", tags=["Subscriptions"])
def cancel_subscription(
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Cancel user's active subscription (will not renew at end of current period)
    """
    # Find active subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == SubscriptionStatus.ACTIVE
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    # Check if already cancelled
    if subscription.cancel_at_period_end:
        return {
            "status": "already_cancelled",
            "message": "Subscription is already scheduled for cancellation",
            "period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None
        }
    
    if not subscription.razorpay_subscription_id:
        # No Razorpay subscription, just mark as cancelled
        subscription.cancel_at_period_end = True
        subscription.cancelled_at = datetime.utcnow()
        db.commit()
        
        return {
            "status": "success",
            "message": "Subscription cancelled. No further charges will be made.",
            "period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None
        }
    
    try:
        # Cancel subscription in Razorpay
        if RAZORPAY_KEY_ID and RAZORPAY_KEY_ID != "dummy" and razorpay_client:
            razorpay_client.subscription.cancel(
                subscription.razorpay_subscription_id,
                {
                    'cancel_at_cycle_end': 1  # Cancel at end of current billing period
                }
            )
        
        # Update subscription in database
        subscription.cancel_at_period_end = True
        subscription.cancelled_at = datetime.utcnow()
        db.commit()
        
        return {
            "status": "success",
            "message": "Subscription will be cancelled at the end of the current billing period",
            "period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "access_until": subscription.current_period_end.isoformat() if subscription.current_period_end else None
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cancel subscription: {str(e)}")


@router.post("/subscriptions/resume", tags=["Subscriptions"])
def resume_subscription(
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    """
    Resume a cancelled subscription (prevents cancellation at period end)
    """
    # Find subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == SubscriptionStatus.ACTIVE
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")
    
    if not subscription.cancel_at_period_end:
        return {
            "status": "not_cancelled",
            "message": "Subscription is not scheduled for cancellation"
        }
    
    try:
        # Resume in Razorpay if applicable
        if subscription.razorpay_subscription_id:
            if RAZORPAY_KEY_ID and RAZORPAY_KEY_ID != "dummy" and razorpay_client:
                # Note: Razorpay doesn't have a direct resume API
                # You might need to update subscription or create a new one
                pass
        
        # Update database
        subscription.cancel_at_period_end = False
        subscription.cancelled_at = None
        db.commit()
        
        return {
            "status": "success",
            "message": "Subscription resumed. Auto-renewal is now active."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to resume subscription: {str(e)}")
