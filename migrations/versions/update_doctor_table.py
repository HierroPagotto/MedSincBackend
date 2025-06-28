"""Update doctor table with new nullable fields

Revision ID: update_doctor_table_v2
Create Date: 2025-05-11 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('doctors', sa.Column('photo_url', sa.String(255), nullable=True))
    op.add_column('doctors', sa.Column('procedures', sa.String(255), nullable=True))
    op.add_column('doctors', sa.Column('shift_types', sa.String(255), nullable=True))
    op.add_column('doctors', sa.Column('preferred_periods', sa.String(255), nullable=True))
    op.add_column('doctors', sa.Column('preferred_days', sa.String(255), nullable=True))
    op.add_column('doctors', sa.Column('accepts_fixed_shifts', sa.Boolean(), nullable=True, server_default=sa.text('1')))
    op.add_column('doctors', sa.Column('accepts_temporary_shifts', sa.Boolean(), nullable=True, server_default=sa.text('1')))
    op.add_column('doctors', sa.Column('max_distance_km', sa.Integer(), nullable=True))
    op.add_column('doctors', sa.Column('state', sa.String(2), nullable=True, server_default='SP'))
    op.add_column('doctors', sa.Column('cities_of_work', sa.String(255), nullable=True))
    op.add_column('doctors', sa.Column('acls', sa.Boolean(), nullable=True, server_default=sa.text('0')))
    op.add_column('doctors', sa.Column('bls', sa.Boolean(), nullable=True, server_default=sa.text('0')))
    op.add_column('doctors', sa.Column('atls', sa.Boolean(), nullable=True, server_default=sa.text('0')))
    op.add_column('doctors', sa.Column('pals', sa.Boolean(), nullable=True, server_default=sa.text('0')))
    op.add_column('doctors', sa.Column('other_certifications', sa.String(255), nullable=True))
    op.add_column('doctors', sa.Column('main_hospitals', sa.String(500), nullable=True))
    op.add_column('doctors', sa.Column('years_of_experience', sa.String(10), nullable=True))
    op.add_column('doctors', sa.Column('has_driver_license', sa.Boolean(), nullable=True, server_default=sa.text('0')))
    op.add_column('doctors', sa.Column('has_ehr_experience', sa.Boolean(), nullable=True, server_default=sa.text('0')))
    op.add_column('doctors', sa.Column('provides_invoice', sa.Boolean(), nullable=True, server_default=sa.text('0')))
    op.add_column('doctors', sa.Column('languages', sa.String(255), nullable=True))
    op.add_column('doctors', sa.Column('is_admin', sa.Boolean(), nullable=True, server_default=sa.text('0')))
    op.add_column('doctors', sa.Column('lost_pass_code', sa.String(6), nullable=True))
    op.add_column('doctors', sa.Column('lost_pass_code_requested_time', sa.DateTime(timezone=True), nullable=True))

def downgrade():
    columns = [
        'photo_url', 'procedures', 'shift_types', 'preferred_periods', 'preferred_days',
        'accepts_fixed_shifts', 'accepts_temporary_shifts', 'max_distance_km', 'state',
        'cities_of_work', 'acls', 'bls', 'atls', 'pals', 'other_certifications',
        'main_hospitals', 'years_of_experience', 'has_driver_license', 'has_ehr_experience',
        'provides_invoice', 'languages', 'is_admin', 'lost_pass_code', 'lost_pass_code_requested_time'
    ]
    for column in columns:
        op.drop_column('doctors', column)
