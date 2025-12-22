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

def seed_plans():
    db = SessionLocal()

    plans = [
        {
            "name": "Free",
            "type": PlanType.FREE,
            "price": 0,
            "currency": "INR",
            "features": '''{
                "ides": "1 IDE",
                "code_runs": "20 runs/month",
                "max_execution_time": "5 seconds",
                "files": "Single file only",
                "history": "No history save",
                "support": "Community support",
                "export": false
            }'''
        },
        {
            "name": "Pro",
            "type": PlanType.PRO,
            "price": 49900,  # ₹499 in paise
            "currency": "INR",
            "features": '''{
                "ides": "1 IDE (full access)",
                "code_runs": "Unlimited",
                "max_execution_time": "Higher limits",
                "files": "Save & reuse code",
                "history": "Execution history",
                "export": "Export output",
                "support": "Email support"
            }'''
        }
    ]

    for plan_data in plans:
        existing = db.query(Plan).filter(Plan.type == plan_data["type"]).first()
        if existing:
            print(f"Plan {plan_data['name']} already exists.")
            continue

        plan = Plan(**plan_data)
        db.add(plan)
        print(f"Added plan {plan_data['name']}.")

    db.commit()
    db.close()
    print("Plans seeded successfully!")

if __name__ == "__main__":
    seed_plans()