"""initial_data_authority_schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-09-25 11:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONType = sa.JSON().with_variant(postgresql.JSONB, "postgresql")

def upgrade() -> None:
    conn = op.get_bind()
    existing_tables = set()
    try:
        if not context.is_offline_mode():
            inspector = sa.inspect(conn)
            existing_tables = set(inspector.get_table_names())
    except Exception:
        existing_tables = set()

    # 1. projects
    if 'projects' not in existing_tables:
        op.create_table(
            'projects',
            sa.Column('id', sa.String(length=64), primary_key=True),
            sa.Column('name', sa.String(length=128), nullable=False),
            sa.Column('niche', sa.String(length=64), nullable=False),
            sa.Column('target_country', sa.String(length=16), default='US'),
            sa.Column('config_json', sa.Text(), default='{}'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )

    # 2. users
    if 'users' not in existing_tables:
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('email', sa.String(length=255), unique=True, nullable=False),
            sa.Column('password_hash', sa.String(length=255), nullable=False),
            sa.Column('salt', sa.String(length=64), nullable=False),
            sa.Column('full_name', sa.String(length=128)),
            sa.Column('plan_tier', sa.String(length=32), default='starter'),
            sa.Column('credits_remaining', sa.Integer(), default=25),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )

    # 3. workspaces
    if 'workspaces' not in existing_tables:
        op.create_table(
            'workspaces',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('name', sa.String(length=128), nullable=False),
            sa.Column('amazon_tag_us', sa.String(length=64), default='yourtag-20'),
            sa.Column('amazon_tag_uk', sa.String(length=64)),
            sa.Column('amazon_tag_ca', sa.String(length=64)),
            sa.Column('amazon_tag_de', sa.String(length=64)),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )

    # 4. connected_sites
    if 'connected_sites' not in existing_tables:
        op.create_table(
            'connected_sites',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
            sa.Column('site_name', sa.String(length=128), nullable=False),
            sa.Column('platform', sa.String(length=32), default='wordpress'),
            sa.Column('site_url', sa.Text(), nullable=False),
            sa.Column('username', sa.String(length=128), nullable=False),
            sa.Column('app_password', sa.Text(), nullable=False),
            sa.Column('status', sa.String(length=32), default='active'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )

    # 5. jobs
    if 'jobs' not in existing_tables:
        op.create_table(
            'jobs',
            sa.Column('id', sa.String(length=64), primary_key=True),
            sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False, default=1),
            sa.Column('project_id', sa.String(length=64), nullable=True),
            sa.Column('job_type', sa.String(length=64), nullable=False),
            sa.Column('status', sa.String(length=32), default='QUEUED'),
            sa.Column('progress', sa.Integer(), default=0),
            sa.Column('retry_count', sa.Integer(), default=0),
            sa.Column('error', sa.Text(), nullable=True),
            sa.Column('input_summary', sa.Text(), nullable=True),
            sa.Column('output_summary', sa.Text(), nullable=True),
            sa.Column('result_json', sa.Text(), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('finished_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )

    # 6. cloaked_links
    if 'cloaked_links' not in existing_tables:
        op.create_table(
            'cloaked_links',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
            sa.Column('slug', sa.String(length=128), unique=True, nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('destination_url', sa.Text(), nullable=False),
            sa.Column('target_country', sa.String(length=16), default='ALL'),
            sa.Column('click_count', sa.Integer(), default=0),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )

    # 7. click_logs
    if 'click_logs' not in existing_tables:
        op.create_table(
            'click_logs',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('link_id', sa.Integer(), sa.ForeignKey('cloaked_links.id', ondelete='CASCADE'), nullable=False),
            sa.Column('slug', sa.String(length=128)),
            sa.Column('ip_hash', sa.String(length=64)),
            sa.Column('referer', sa.Text()),
            sa.Column('user_agent', sa.Text()),
            sa.Column('clicked_at', sa.DateTime(), nullable=True),
        )

    # 8. sentiment_cache
    if 'sentiment_cache' not in existing_tables:
        op.create_table(
            'sentiment_cache',
            sa.Column('asin', sa.String(length=64), primary_key=True),
            sa.Column('product_name', sa.String(length=255)),
            sa.Column('complaints_json', sa.Text()),
            sa.Column('praises_json', sa.Text()),
            sa.Column('verified_quotes_json', sa.Text()),
            sa.Column('rating', sa.Float()),
            sa.Column('mined_at', sa.DateTime(), nullable=True),
        )

    # 9. articles
    if 'articles' not in existing_tables:
        op.create_table(
            'articles',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('workspace_id', sa.Integer(), default=1),
            sa.Column('site_id', sa.Integer(), nullable=True),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('slug', sa.String(length=255)),
            sa.Column('keyword', sa.String(length=255), nullable=False),
            sa.Column('asins', sa.Text()),
            sa.Column('status', sa.String(length=32), default='draft'),
            sa.Column('wp_post_id', sa.Integer()),
            sa.Column('wp_link', sa.Text()),
            sa.Column('eeat_score', sa.Integer(), default=0),
            sa.Column('file_path', sa.Text()),
            sa.Column('page_type', sa.String(length=32), default='review'),
            sa.Column('primary_entity_id', sa.String(length=64)),
            sa.Column('quality_score', sa.Float()),
            sa.Column('quality_decision', sa.String(length=32)),
            sa.Column('last_verified_at', sa.DateTime()),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )

    # 10. rank_history
    if 'rank_history' not in existing_tables:
        op.create_table(
            'rank_history',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('workspace_id', sa.Integer(), default=1),
            sa.Column('keyword', sa.String(length=255), nullable=False),
            sa.Column('domain', sa.String(length=128)),
            sa.Column('rank_position', sa.Integer()),
            sa.Column('status_message', sa.Text()),
            sa.Column('checked_at', sa.DateTime(), nullable=True),
        )

    # 11. campaign_plans
    if 'campaign_plans' not in existing_tables:
        op.create_table(
            'campaign_plans',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('workspace_id', sa.Integer(), default=1),
            sa.Column('category_name', sa.String(length=128), nullable=False),
            sa.Column('category_url', sa.Text()),
            sa.Column('total_items', sa.Integer(), default=30),
            sa.Column('status', sa.String(length=32), default='ready'),
            sa.Column('summary_json', sa.Text()),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )

    # 12. scheduled_posts
    if 'scheduled_posts' not in existing_tables:
        op.create_table(
            'scheduled_posts',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('plan_id', sa.Integer(), sa.ForeignKey('campaign_plans.id', ondelete='CASCADE'), nullable=True),
            sa.Column('workspace_id', sa.Integer(), default=1),
            sa.Column('site_id', sa.Integer(), nullable=True),
            sa.Column('day_number', sa.Integer(), nullable=False),
            sa.Column('publish_date', sa.String(length=32), nullable=False),
            sa.Column('article_type', sa.String(length=32), nullable=False),
            sa.Column('keyword', sa.String(length=255), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('asins_json', sa.Text()),
            sa.Column('status', sa.String(length=32), default='pending'),
            sa.Column('wp_post_id', sa.Integer()),
            sa.Column('wp_link', sa.Text()),
            sa.Column('preview_file', sa.Text()),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )

    # 13. entities
    if 'entities' not in existing_tables:
        op.create_table(
            'entities',
            sa.Column('id', sa.String(length=64), primary_key=True),
            sa.Column('project_id', sa.String(length=64), nullable=True),
            sa.Column('entity_type', sa.String(length=32), nullable=False),
            sa.Column('brand', sa.String(length=64), nullable=False),
            sa.Column('model', sa.String(length=128), nullable=False),
            sa.Column('sku_or_upc', sa.String(length=64)),
            sa.Column('primary_image_url', sa.Text()),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )

    # 14. sources
    if 'sources' not in existing_tables:
        op.create_table(
            'sources',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('entity_id', sa.String(length=64), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False),
            sa.Column('source_type', sa.String(length=32), nullable=False),
            sa.Column('priority', sa.Integer(), default=3),
            sa.Column('url', sa.Text()),
            sa.Column('document_title', sa.Text()),
            sa.Column('http_status', sa.Integer(), default=200),
            sa.Column('content_hash', sa.String(length=64)),
            sa.Column('parser_version', sa.String(length=16), default='1.0'),
            sa.Column('is_stale', sa.Boolean(), default=False),
            sa.Column('snapshot_archive_path', sa.Text()),
            sa.Column('fetched_at', sa.DateTime(), nullable=True),
        )

    # 15. entity_attributes
    if 'entity_attributes' not in existing_tables:
        op.create_table(
            'entity_attributes',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('entity_id', sa.String(length=64), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False),
            sa.Column('attr_key', sa.String(length=64), nullable=False),
            sa.Column('attr_value_num', sa.Float()),
            sa.Column('attr_value_text', sa.Text()),
            sa.Column('unit', sa.String(length=16)),
            sa.Column('confidence_score', sa.Float(), default=1.0),
            sa.Column('verified_by_source_id', sa.Integer(), sa.ForeignKey('sources.id')),
            sa.Column('is_unknown', sa.Boolean(), default=False),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )
        op.create_index('idx_entity_attr', 'entity_attributes', ['entity_id', 'attr_key'])

    # 16. evidence_claims
    if 'evidence_claims' not in existing_tables:
        op.create_table(
            'evidence_claims',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('entity_id', sa.String(length=64), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False),
            sa.Column('source_id', sa.Integer(), sa.ForeignKey('sources.id', ondelete='CASCADE'), nullable=False),
            sa.Column('attribute_key', sa.String(length=64), nullable=False),
            sa.Column('extracted_value', sa.Text(), nullable=False),
            sa.Column('raw_quote', sa.Text(), nullable=False),
            sa.Column('page_number', sa.Integer()),
            sa.Column('status', sa.String(length=16), default='VERIFIED'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )

    # 17. compatibility_matrix
    if 'compatibility_matrix' not in existing_tables:
        op.create_table(
            'compatibility_matrix',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('subject_entity_id', sa.String(length=64), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False),
            sa.Column('target_entity_id', sa.String(length=64), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False),
            sa.Column('compatibility_status', sa.String(length=16), nullable=False),
            sa.Column('fit_detail', sa.Text()),
            sa.Column('max_clearance_inches', sa.Float()),
            sa.Column('confidence', sa.Float(), default=1.0),
            sa.Column('tested_method', sa.String(length=32), default='CALCULATED_DIMENSION'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )

    # 18. merchant_offers
    if 'merchant_offers' not in existing_tables:
        op.create_table(
            'merchant_offers',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('entity_id', sa.String(length=64), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False),
            sa.Column('merchant_name', sa.String(length=32), nullable=False),
            sa.Column('external_id', sa.String(length=64), nullable=False),
            sa.Column('affiliate_url', sa.Text(), nullable=False),
            sa.Column('current_price', sa.Float()),
            sa.Column('currency', sa.String(length=8), default='USD'),
            sa.Column('in_stock', sa.Boolean(), default=True),
            sa.Column('offer_status', sa.String(length=16), default='ACTIVE'),
            sa.Column('rating', sa.Float()),
            sa.Column('review_count', sa.Integer(), default=0),
            sa.Column('last_checked_at', sa.DateTime(), nullable=True),
        )
        op.create_index('idx_merchant_entity', 'merchant_offers', ['entity_id', 'merchant_name'])

    # 19. attribute_definitions
    if 'attribute_definitions' not in existing_tables:
        op.create_table(
            'attribute_definitions',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('attr_key', sa.String(length=64), unique=True, nullable=False),
            sa.Column('display_name', sa.String(length=128), nullable=False),
            sa.Column('data_type', sa.String(length=16), default='numeric'),
            sa.Column('default_unit', sa.String(length=16)),
            sa.Column('description', sa.Text()),
        )

    # 20. entity_relationships
    if 'entity_relationships' not in existing_tables:
        op.create_table(
            'entity_relationships',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('subject_id', sa.String(length=64), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False),
            sa.Column('predicate', sa.String(length=64), nullable=False),
            sa.Column('object_id', sa.String(length=64), sa.ForeignKey('entities.id', ondelete='CASCADE'), nullable=False),
            sa.Column('confidence', sa.Float(), default=1.0),
            sa.Column('source_id', sa.Integer(), sa.ForeignKey('sources.id')),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
        op.create_index('idx_rel_subj_obj', 'entity_relationships', ['subject_id', 'object_id'])

    # 21. calculation_logs
    if 'calculation_logs' not in existing_tables:
        op.create_table(
            'calculation_logs',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('entity_id', sa.String(length=64)),
            sa.Column('calculation_type', sa.String(length=64), nullable=False),
            sa.Column('inputs_json', sa.Text(), nullable=False),
            sa.Column('formula_version', sa.String(length=16), default='v1.0'),
            sa.Column('assumptions_json', sa.Text(), nullable=False),
            sa.Column('output_json', sa.Text(), nullable=False),
            sa.Column('executed_at', sa.DateTime(), nullable=True),
        )

    # 22. page_plans
    if 'page_plans' not in existing_tables:
        op.create_table(
            'page_plans',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('workspace_id', sa.Integer(), default=1),
            sa.Column('project_id', sa.String(length=64)),
            sa.Column('target_keyword', sa.Text(), nullable=False),
            sa.Column('intent_type', sa.String(length=32), nullable=False),
            sa.Column('cluster_id', sa.String(length=64)),
            sa.Column('plan_action', sa.String(length=32), default='CREATE'),
            sa.Column('target_entity_ids', sa.Text()),
            sa.Column('factual_brief_json', sa.Text()),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )

    # 23. page_quality_evaluations
    if 'page_quality_evaluations' not in existing_tables:
        op.create_table(
            'page_quality_evaluations',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('page_plan_id', sa.Integer(), sa.ForeignKey('page_plans.id')),
            sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id')),
            sa.Column('overall_score', sa.Float(), nullable=False),
            sa.Column('status', sa.String(length=16), nullable=False),
            sa.Column('quality_breakdown_json', sa.Text(), nullable=False),
            sa.Column('hard_blockers_json', sa.Text(), default='[]'),
            sa.Column('evaluated_at', sa.DateTime(), nullable=True),
        )

    # 24. claim_validations
    if 'claim_validations' not in existing_tables:
        op.create_table(
            'claim_validations',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('article_id', sa.Integer(), sa.ForeignKey('articles.id')),
            sa.Column('claim_text', sa.Text(), nullable=False),
            sa.Column('fact_id', sa.String(length=64)),
            sa.Column('calculation_id', sa.Integer()),
            sa.Column('evidence_id', sa.Integer(), sa.ForeignKey('evidence_claims.id')),
            sa.Column('source_id', sa.Integer(), sa.ForeignKey('sources.id')),
            sa.Column('validation_status', sa.String(length=16), nullable=False),
            sa.Column('matched_attribute_id', sa.Integer(), sa.ForeignKey('entity_attributes.id')),
            sa.Column('reason', sa.Text()),
            sa.Column('validated_at', sa.DateTime(), nullable=True),
        )

    # 25. gsc_metrics
    if 'gsc_metrics' not in existing_tables:
        op.create_table(
            'gsc_metrics',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('workspace_id', sa.Integer(), default=1),
            sa.Column('page_url', sa.Text(), nullable=False),
            sa.Column('query', sa.Text(), nullable=False),
            sa.Column('impressions', sa.Integer(), default=0),
            sa.Column('clicks', sa.Integer(), default=0),
            sa.Column('ctr', sa.Float(), default=0.0),
            sa.Column('position', sa.Float(), default=0.0),
            sa.Column('recorded_date', sa.Date(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.UniqueConstraint('page_url', 'query', 'recorded_date', name='uq_gsc_url_query_date')
        )
        op.create_index('idx_gsc_url_query', 'gsc_metrics', ['page_url', 'query'])
        op.create_index('idx_gsc_date', 'gsc_metrics', ['recorded_date'])

    # 26. audit_logs
    if 'audit_logs' not in existing_tables:
        op.create_table(
            'audit_logs',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('workspace_id', sa.Integer(), default=1),
            sa.Column('action', sa.String(length=64), nullable=False),
            sa.Column('entity_type', sa.String(length=32)),
            sa.Column('entity_id', sa.String(length=64)),
            sa.Column('actor', sa.String(length=64), default='system'),
            sa.Column('details_json', sa.Text()),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
        op.create_index('idx_audit_action', 'audit_logs', ['action', 'entity_id'])

    # 27. internal_links
    if 'internal_links' not in existing_tables:
        op.create_table(
            'internal_links',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('workspace_id', sa.Integer(), default=1),
            sa.Column('source_url', sa.Text(), nullable=False),
            sa.Column('target_url', sa.Text(), nullable=False),
            sa.Column('anchor_text', sa.String(length=255), nullable=False),
            sa.Column('anchor_type', sa.String(length=32), default='natural'),
            sa.Column('context_snippet', sa.Text()),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
        op.create_index('idx_internal_link_source', 'internal_links', ['source_url'])
        op.create_index('idx_internal_link_target', 'internal_links', ['target_url'])


def downgrade() -> None:
    tables = [
        'internal_links', 'audit_logs', 'gsc_metrics', 'claim_validations',
        'page_quality_evaluations', 'page_plans', 'calculation_logs',
        'entity_relationships', 'attribute_definitions', 'merchant_offers',
        'compatibility_matrix', 'evidence_claims', 'entity_attributes',
        'sources', 'entities', 'scheduled_posts', 'campaign_plans',
        'rank_history', 'articles', 'sentiment_cache', 'click_logs',
        'cloaked_links', 'jobs', 'connected_sites', 'workspaces', 'users', 'projects'
    ]
    for table in tables:
        op.drop_table(table)
