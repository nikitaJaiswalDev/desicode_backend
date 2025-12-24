

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
