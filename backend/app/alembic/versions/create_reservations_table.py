"""create reservations table

Revision ID: 002_create_reservations_table
Revises: 001_create_restaurant_table
Create Date: 2024-03-21
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '002_create_reservations_table'
down_revision = '001_create_restaurant_table'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'reservations',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('restaurant_id', sa.Integer, sa.ForeignKey('restaurants.id'), nullable=False),
        sa.Column('restaurant_name', sa.String(100), nullable=False),
        sa.Column('customer_name', sa.String(100), nullable=False),
        sa.Column('customer_phone', sa.String(20), nullable=False),
        sa.Column('reservation_date', sa.Date, nullable=False),
        sa.Column('reservation_time', sa.Time, nullable=False),
        sa.Column('number_of_people', sa.Integer, nullable=False),
        sa.Column('special_requests', sa.Text, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),  # pending, confirmed, cancelled
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )

def downgrade():
    op.drop_table('reservations') 