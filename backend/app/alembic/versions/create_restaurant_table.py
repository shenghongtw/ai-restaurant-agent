"""create restaurant table

Revision ID: 001_create_restaurant_table
Revises: 
Create Date: 2024-03-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import String, Float, JSON

# revision identifiers, used by Alembic
revision = '001_create_restaurant_table'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 創建餐廳表
    op.create_table(
        'restaurants',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('business_time', JSON, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('menu_items', JSON, nullable=True),
        sa.Column('address', sa.String(200), nullable=True),
        sa.Column('longitude', sa.Float, nullable=True),
        sa.Column('latitude', sa.Float, nullable=True),
        sa.Column('price_range', sa.String(50), nullable=True)
    )

    # 插入示例數據
    op.execute("""
    INSERT INTO restaurants (name, business_time, description, menu_items, address, longitude, latitude, price_range)
    VALUES 
    (
        '大麥',
        '{"monday": "09:00-21:00", "tuesday": "09:00-21:00", "wednesday": "09:00-21:00", "thursday": "09:00-21:00", "friday": "09:00-22:00", "saturday": "10:00-22:00", "sunday": "10:00-21:00"}',
        '這是一家提供美味料理的餐廳',
        '["牛肉麵", "滷肉飯", "炒青菜", "紅燒魚"]',
        '台北市中山區中山北路一段',
        121.5200,
        25.0500,
        '200-500'
    ),
    (
        '小麥',
        '{"monday": "09:00-21:00", "tuesday": "09:00-21:00", "wednesday": "09:00-21:00", "thursday": "09:00-21:00", "friday": "09:00-22:00", "saturday": "10:00-22:00", "sunday": "10:00-21:00"}',
        '這是一家提供美味料理的餐廳',
        '["滷肉飯", "炒青菜", "獅子頭"]',
        '台北市中山區中山北路一段',
        121.5200,
        25.0500,
        '200-500'
    ),
    (
        '小小麥',
        '{"monday": "09:00-21:00", "tuesday": "09:00-21:00", "wednesday": "09:00-21:00", "thursday": "09:00-21:00", "friday": "09:00-22:00", "saturday": "10:00-22:00", "sunday": "10:00-21:00"}',
        '這是一家提供美味料理的餐廳',
        '["滷肉飯", "茄子"]',
        '台北市中山區中山北路一段',
        121.5200,
        25.0500,
        '200-500'
    ),
    (
        '日式料理店',
        '{"monday": "11:30-21:00", "tuesday": "11:30-21:00", "wednesday": "11:30-21:00", "thursday": "11:30-21:00", "friday": "11:30-22:00", "saturday": "11:30-22:00", "sunday": "休息"}',
        '正統日本料理，提供新鮮生魚片與各式壽司',
        '["生魚片", "握壽司", "烤鯖魚", "味噌湯"]',
        '台北市信義區松仁路',
        121.5680,
        25.0330,
        '500-1000'
    ),
    (
        '義大利餐廳',
        '{"monday": "休息", "tuesday": "17:30-22:00", "wednesday": "17:30-22:00", "thursday": "17:30-22:00", "friday": "17:30-23:00", "saturday": "11:30-23:00", "sunday": "11:30-22:00"}',
        '道地義式料理，手工現製義大利麵',
        '["白醬義大利麵", "瑪格麗特披薩", "燉飯", "提拉米蘇"]',
        '台北市大安區敦化南路',
        121.5480,
        25.0280,
        '600-1200'
    )
    """)

def downgrade():
    # 刪除餐廳表
    op.drop_table('restaurants')