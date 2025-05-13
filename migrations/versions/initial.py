"""Initial migration with adjusted nullable fields

Revision ID: initial
Create Date: 2025-05-11 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'doctors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(100), unique=True, nullable=True),
        sa.Column('password', sa.String(255), nullable=False),
        sa.Column('crm', sa.String(20), unique=True, nullable=True),
        sa.Column('crm_state', sa.String(2), nullable=True),
        sa.Column('graduation_year', sa.Integer(), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('main_specialty', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'hospitals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('address', sa.String(255), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'shifts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=False),
        sa.Column('hospital_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('value', sa.Numeric(10, 2), nullable=False),
        sa.Column('specialty', sa.String(100), nullable=True),
        sa.Column('payment_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id']),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shift_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('payment_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['shift_id'], ['shifts.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index('idx_shifts_doctor_id', 'shifts', ['doctor_id'])
    op.create_index('idx_shifts_hospital_id', 'shifts', ['hospital_id'])
    op.create_index('idx_payments_shift_id', 'payments', ['shift_id'])


def downgrade():
    op.drop_index('idx_payments_shift_id', table_name='payments')
    op.drop_index('idx_shifts_hospital_id', table_name='shifts')
    op.drop_index('idx_shifts_doctor_id', table_name='shifts')
    op.drop_table('payments')
    op.drop_table('shifts')
    op.drop_table('hospitals')
    op.drop_table('doctors')
