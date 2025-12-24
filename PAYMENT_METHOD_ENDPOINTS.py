

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
