import sys
import os
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import ALL models to ensure they're registered with SQLAlchemy
from app.models.user import User
from app.models.subscription import Plan, PlanType, Subscription
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.code_execution import CodeExecution
from app.models.language import Language

# Now import session
from app.db.session import SessionLocal

def cleanup_old_plans():
    """Delete old plans and ensure only Free and Pro exist"""
    db = SessionLocal()
    
    try:
        print("Starting plan cleanup...")
        
        # First, create the new plans if they don't exist
        print("\n1. Creating/Updating Free and Pro plans...")
        
        # Check if Free plan exists
        free_plan = db.query(Plan).filter(Plan.name == "Free").first()
        if not free_plan:
            free_plan = Plan(
                name="Free",
                type=PlanType.FREE,
                price=0,
                currency="INR",
                features='''{
                    "ides": "1 IDE",
                    "code_runs": "20 runs/month",
                    "max_execution_time": "5 seconds",
                    "files": "Single file only",
                    "history": "No history save",
                    "support": "Community support",
                    "export": false
                }'''
            )
            db.add(free_plan)
            db.flush()
            print(f"  ✅ Created Free plan (ID: {free_plan.id})")
        else:
            # Update existing Free plan
            free_plan.type = PlanType.FREE
            free_plan.features = '''{
                "ides": "1 IDE",
                "code_runs": "20 runs/month",
                "max_execution_time": "5 seconds",
                "files": "Single file only",
                "history": "No history save",
                "support": "Community support",
                "export": false
            }'''
            print(f"  ✅ Updated Free plan (ID: {free_plan.id})")
        
        # Check if Pro plan exists
        pro_plan = db.query(Plan).filter(Plan.name == "Pro").first()
        if not pro_plan:
            pro_plan = Plan(
                name="Pro",
                type=PlanType.PRO,
                price=49900,
                currency="INR",
                features='''{
                    "ides": "1 IDE (full access)",
                    "code_runs": "Unlimited",
                    "max_execution_time": "Higher limits",
                    "files": "Save & reuse code",
                    "history": "Execution history",
                    "export": "Export output",
                    "support": "Email support"
                }'''
            )
            db.add(pro_plan)
            db.flush()
            print(f"  ✅ Created Pro plan (ID: {pro_plan.id})")
        else:
            # Update existing Pro plan
            pro_plan.type = PlanType.PRO
            pro_plan.price = 49900
            pro_plan.features = '''{
                "ides": "1 IDE (full access)",
                "code_runs": "Unlimited",
                "max_execution_time": "Higher limits",
                "files": "Save & reuse code",
                "history": "Execution history",
                "export": "Export output",
                "support": "Email support"
            }'''
            print(f"  ✅ Updated Pro plan (ID: {pro_plan.id})")
        
        db.commit()
        
        # Update subscriptions pointing to old plans
        print("\n2. Migrating subscriptions from old plans to Free...")
        old_plan_names = ["Starter", "Team", "Campus", "Enterprise"]
        total_migrated = 0
        for old_name in old_plan_names:
            old_plan = db.query(Plan).filter(Plan.name == old_name).first()
            if old_plan:
                # Move all subscriptions to Free plan
                updated = db.query(Subscription).filter(
                    Subscription.plan_id == old_plan.id
                ).update({"plan_id": free_plan.id})
                if updated > 0:
                    total_migrated += updated
                    print(f"  ✅ Moved {updated} subscriptions from {old_name} to Free")
        
        if total_migrated == 0:
            print("  ℹ️  No subscriptions to migrate")
        
        db.commit()
        
        # Now delete old plans
        print("\n3. Deleting old plans...")
        deleted_count = 0
        for old_name in old_plan_names:
            old_plan = db.query(Plan).filter(Plan.name == old_name).first()
            if old_plan:
                db.delete(old_plan)
                deleted_count += 1
                print(f"  ✅ Deleted {old_name} plan")
        
        if deleted_count == 0:
            print("  ℹ️  No old plans to delete")
        
        db.commit()
        
        print("\n🎉 Plans cleanup completed successfully!")
        print("\n" + "="*50)
        print("Current plans in database:")
        print("="*50)
        all_plans = db.query(Plan).all()
        for p in all_plans:
            price = p.price / 100 if p.price > 0 else 0
            print(f"  📋 {p.name}")
            print(f"     ID: {p.id}")
            print(f"     Type: {p.type.value}")
            print(f"     Price: {p.currency} {price}")
            print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_old_plans()
