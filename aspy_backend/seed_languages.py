from app.db.session import SessionLocal
from app.models.language import Language
from app.models.code_execution import CodeExecution
from app.models.user import User
from app.models.subscription import Subscription, Plan
from app.models.invoice import Invoice
from app.models.payment import Payment

db = SessionLocal()
languages = [
    {'name': 'English', 'slug': 'english'},
    {'name': 'Assamese', 'slug': 'assamese'},
    {'name': 'Bengali', 'slug': 'bengali'},
    {'name': 'Bodo', 'slug': 'bodo'},
    {'name': 'Manipuri', 'slug': 'manipuri'},
    {'name': 'Khasi', 'slug': 'khasi'},
    {'name': 'Garo', 'slug': 'garo'},
    {'name': 'Mizo', 'slug': 'mizo'}
]

for lang in languages:
    existing = db.query(Language).filter(Language.slug == lang['slug']).first()
    if not existing:
        db.add(Language(name=lang['name'], slug=lang['slug']))
        print(f'Added {lang['name']}')

db.commit()
print('Languages seeded.')
