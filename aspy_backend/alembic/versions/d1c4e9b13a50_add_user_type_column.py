"""add_user_type_column

Revision ID: d1c4e9b13a50
Revises: add_razorpay_customer_card
Create Date: 2025-12-25 19:36:03.683078

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1c4e9b13a50'
down_revision: Union[str, None] = 'add_razorpay_customer_card'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type for user_type with uppercase values to match Python enum
    user_type_enum = sa.Enum('USER', 'ADMIN', name='usertype')
    user_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Add user_type column with default value 'USER'
    op.add_column('users', sa.Column('user_type', user_type_enum, nullable=False, server_default='USER'))


def downgrade() -> None:
    # Remove user_type column
    op.drop_column('users', 'user_type')
    
    # Drop enum type
    sa.Enum(name='usertype').drop(op.get_bind(), checkfirst=True)