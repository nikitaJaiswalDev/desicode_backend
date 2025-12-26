"""
Script to create an admin user in the database
Usage: python create_admin.py
"""
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User, UserType
from app.core.security import hash_password
import sys

def create_admin_user(email: str, username: str, password: str):
    """Create an admin user"""
    db: Session = SessionLocal()
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"User with email {email} already exists.")
            
            # Update to admin if not already
            if existing_user.user_type != UserType.ADMIN:
                existing_user.user_type = UserType.ADMIN
                db.commit()
                print(f"User {email} has been upgraded to admin.")
            else:
                print(f"User {email} is already an admin.")
            return
        
        # Create new admin user
        admin_user = User(
            email=email,
            username=username,
            password=hash_password(password),
            user_type=UserType.ADMIN,
            is_active=True,
            is_superuser=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print(f"✅ Admin user created successfully!")
        print(f"Email: {email}")
        print(f"Username: {username}")
        print(f"User Type: {admin_user.user_type.value}")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("=== Create Admin User ===")
    
    # You can modify these or take them as input
    email = input("Enter admin email: ").strip()
    username = input("Enter admin username: ").strip()
    password = input("Enter admin password: ").strip()
    
    if not email or not username or not password:
        print("❌ All fields are required!")
        sys.exit(1)
    
    create_admin_user(email, username, password)
