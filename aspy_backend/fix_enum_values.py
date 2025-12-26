"""
Fix subscription and plan enum values in the database
This script updates any lowercase enum values to uppercase
"""
from sqlalchemy import text
from app.db.session import SessionLocal

def fix_enum_values():
    """Update enum values from lowercase to uppercase"""
    db = SessionLocal()
    
    try:
        print("=== Fixing Subscription Status Enum Values ===\n")
        
        # Check current subscription statuses
        print("Checking current subscription statuses...")
        result = db.execute(text("SELECT id, user_id, status FROM subscriptions"))
        subscriptions = result.fetchall()
        
        if subscriptions:
            print(f"Found {len(subscriptions)} subscriptions:")
            for sub in subscriptions:
                print(f"  ID: {sub.id}, User: {sub.user_id}, Status: {sub.status}")
        else:
            print("  No subscriptions found")
        
        # Update subscription statuses
        print("\nUpdating subscription status values...")
        updates = [
            ("active", "ACTIVE"),
            ("cancelled", "CANCELLED"),
            ("expired", "EXPIRED"),
            ("past_due", "PAST_DUE")
        ]
        
        total_updated = 0
        for old_val, new_val in updates:
            result = db.execute(
                text(f"UPDATE subscriptions SET status = '{new_val}' WHERE status = '{old_val}'")
            )
            if result.rowcount > 0:
                print(f"  Updated {result.rowcount} subscriptions from '{old_val}' to '{new_val}'")
                total_updated += result.rowcount
        
        if total_updated == 0:
            print("  No subscription statuses needed updating")
        
        print("\n=== Fixing Plan Type Enum Values ===\n")
        
        # Check current plan types
        print("Checking current plan types...")
        result = db.execute(text("SELECT id, name, type FROM plans"))
        plans = result.fetchall()
        
        if plans:
            print(f"Found {len(plans)} plans:")
            for plan in plans:
                print(f"  ID: {plan.id}, Name: {plan.name}, Type: {plan.type}")
        else:
            print("  No plans found")
        
        # Update plan types
        print("\nUpdating plan type values...")
        plan_updates = [
            ("free", "FREE"),
            ("pro", "PRO")
        ]
        
        plan_total_updated = 0
        for old_val, new_val in plan_updates:
            result = db.execute(
                text(f"UPDATE plans SET type = '{new_val}' WHERE type = '{old_val}'")
            )
            if result.rowcount > 0:
                print(f"  Updated {result.rowcount} plans from '{old_val}' to '{new_val}'")
                plan_total_updated += result.rowcount
        
        if plan_total_updated == 0:
            print("  No plan types needed updating")
        
        db.commit()
        
        # Verify changes
        print("\n=== Verification ===\n")
        
        print("Current subscription statuses:")
        result = db.execute(text("SELECT DISTINCT status FROM subscriptions"))
        statuses = result.fetchall()
        for status in statuses:
            print(f"  - {status.status}")
        
        print("\nCurrent plan types:")
        result = db.execute(text("SELECT id, name, type FROM plans"))
        plans = result.fetchall()
        for plan in plans:
            print(f"  ID: {plan.id}, Name: {plan.name}, Type: {plan.type}")
        
        print("\n✅ Enum values fixed successfully!")
        
    except Exception as e:
        print(f"❌ Error fixing enum values: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_enum_values()
