"""add razorpay customer and card details

Revision ID: add_razorpay_customer_card
Revises: 
Create Date: 2025-12-24 13:10:00
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_razorpay_customer_card'
down_revision = '8a34b21e876d'  # Latest database revision
branch_labels = None
depends_on = None


def upgrade():
    # Add card details to subscriptions table for display purposes
    op.add_column('subscriptions', sa.Column('card_last4', sa.String(4), nullable=True))
    op.add_column('subscriptions', sa.Column('card_brand', sa.String(50), nullable=True))
    op.add_column('subscriptions', sa.Column('card_exp_month', sa.Integer(), nullable=True))
    op.add_column('subscriptions', sa.Column('card_exp_year', sa.Integer(), nullable=True))


def downgrade():
    # Remove card details from subscriptions
    op.drop_column('subscriptions', 'card_exp_year')
    op.drop_column('subscriptions', 'card_exp_month')
    op.drop_column('subscriptions', 'card_brand')
    op.drop_column('subscriptions', 'card_last4')
