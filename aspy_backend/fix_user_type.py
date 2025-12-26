"""
Fix user_type enum values in the database
This script updates any lowercase enum values to uppercase
"""
from sqlalchemy import text
from app.db.session import SessionLocal

def fix_user_type_enum():
    """Update user_type enum values from lowercase to uppercase"""
    db = SessionLocal()
    
    try:
        # Check current state
        print("Checking current user_type values...")
        result = db.execute(text("SELECT id, email, user_type FROM users"))
        users = result.fetchall()
        
        print(f"\nFound {len(users)} users:")
        for user in users:
            print(f"  ID: {user.id}, Email: {user.email}, Type: {user.user_type}")
        
        # Update lowercase values to uppercase
        print("\nUpdating user_type values...")
        
        # Update 'user' to 'USER'
        result_user = db.execute(
            text("UPDATE users SET user_type = 'USER' WHERE user_type = 'user'")
        )
        print(f"  Updated {result_user.rowcount} users from 'user' to 'USER'")
        
        # Update 'admin' to 'ADMIN'
        result_admin = db.execute(
            text("UPDATE users SET user_type = 'ADMIN' WHERE user_type = 'admin'")
        )
        print(f"  Updated {result_admin.rowcount} users from 'admin' to 'ADMIN'")
        
        db.commit()
        
        # Verify changes
        print("\nVerifying changes...")
        result = db.execute(text("SELECT id, email, user_type, is_superuser FROM users"))
        users = result.fetchall()
        
        print(f"\nCurrent state of all users:")
        for user in users:
            print(f"  ID: {user.id}, Email: {user.email}, Type: {user.user_type}, Superuser: {user.is_superuser}")
        
        print("\n✅ User type enum values fixed successfully!")
        
    except Exception as e:
        print(f"❌ Error fixing user types: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("=== Fix User Type Enum Values ===\n")
    fix_user_type_enum()
