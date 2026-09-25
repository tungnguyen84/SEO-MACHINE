"""durable_jobs_and_credentials

Revision ID: 002_durable_jobs
Revises: 001_initial
Create Date: 2026-09-25 23:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_durable_jobs'
down_revision: Union[str, Sequence[str], None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. Create site_credentials table
    if 'site_credentials' not in existing_tables:
        op.create_table(
            'site_credentials',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('tenant_id', sa.String(length=64), nullable=False),
            sa.Column('site_id', sa.String(length=128), nullable=False),
            sa.Column('key_name', sa.String(length=128), nullable=False),
            sa.Column('encrypted_value', sa.Text(), nullable=False),
            sa.Column('key_version', sa.Integer(), server_default='1', nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.UniqueConstraint('site_id', 'key_name', name='uq_site_credential_key'),
        )
        op.create_index('idx_site_cred_tenant', 'site_credentials', ['tenant_id', 'site_id'])

    # 2. Add columns to jobs table
    job_columns = {col['name'] for col in inspector.get_columns('jobs')}

    if 'tenant_id' not in job_columns:
        op.add_column('jobs', sa.Column('tenant_id', sa.String(length=64), nullable=True))
    if 'site_id' not in job_columns:
        op.add_column('jobs', sa.Column('site_id', sa.String(length=128), nullable=True))
    if 'idempotency_key' not in job_columns:
        op.add_column('jobs', sa.Column('idempotency_key', sa.String(length=128), nullable=True))
        op.create_index('idx_jobs_idempotency', 'jobs', ['idempotency_key'])
    if 'payload_json' not in job_columns:
        op.add_column('jobs', sa.Column('payload_json', sa.Text(), nullable=True))
    if 'locked_by' not in job_columns:
        op.add_column('jobs', sa.Column('locked_by', sa.String(length=128), nullable=True))
    if 'locked_at' not in job_columns:
        op.add_column('jobs', sa.Column('locked_at', sa.DateTime(), nullable=True))
    if 'lease_expires_at' not in job_columns:
        op.add_column('jobs', sa.Column('lease_expires_at', sa.DateTime(), nullable=True))
        op.create_index('idx_jobs_lease', 'jobs', ['status', 'lease_expires_at'])
    if 'max_retries' not in job_columns:
        op.add_column('jobs', sa.Column('max_retries', sa.Integer(), server_default='3', nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if 'site_credentials' in existing_tables:
        op.drop_table('site_credentials')

    job_columns = {col['name'] for col in inspector.get_columns('jobs')}
    for col in ['max_retries', 'lease_expires_at', 'locked_at', 'locked_by', 'payload_json', 'idempotency_key', 'site_id', 'tenant_id']:
        if col in job_columns:
            op.drop_column('jobs', col)
