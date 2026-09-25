"""
SQLAlchemy Models for OpenSEO Data Authority Engine
Supports both PostgreSQL (Production) and SQLite (Local / Test).
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, DateTime, Date,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa

Base = declarative_base()

# Portable JSON type: JSONB on PostgreSQL, JSON/Text on SQLite
JSONType = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


class Project(Base):
    """Project Configuration and Target Niche"""
    __tablename__ = "projects"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    niche = Column(String(64), nullable=False)
    target_country = Column(String(16), default="US")
    config_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):
    """Multi-tenant User Accounts"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(64), nullable=False)
    full_name = Column(String(128))
    plan_tier = Column(String(32), default="starter")
    credits_remaining = Column(Integer, default=25)
    created_at = Column(DateTime, default=datetime.utcnow)

    workspaces = relationship("Workspace", back_populates="user", cascade="all, delete-orphan")


class Workspace(Base):
    """Workspace Isolation for Projects & Credentials"""
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(128), nullable=False)
    amazon_tag_us = Column(String(64), default="yourtag-20")
    amazon_tag_uk = Column(String(64))
    amazon_tag_ca = Column(String(64))
    amazon_tag_de = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="workspaces")
    sites = relationship("ConnectedSite", back_populates="workspace", cascade="all, delete-orphan")


class ConnectedSite(Base):
    """WordPress / CMS Endpoints"""
    __tablename__ = "connected_sites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    site_name = Column(String(128), nullable=False)
    platform = Column(String(32), default="wordpress")
    site_url = Column(Text, nullable=False)
    username = Column(String(128), nullable=False)
    app_password = Column(Text, nullable=False)
    status = Column(String(32), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    workspace = relationship("Workspace", back_populates="sites")


class Job(Base):
    """Observable Background Tasks with Multi-Worker Distributed Leases"""
    __tablename__ = "jobs"

    id = Column(String(64), primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, default=1)
    project_id = Column(String(64), nullable=True)
    tenant_id = Column(String(64), nullable=True, index=True)
    site_id = Column(String(128), nullable=True, index=True)
    job_type = Column(String(64), nullable=False)
    status = Column(String(32), default="QUEUED")  # QUEUED, RUNNING, SUCCEEDED, FAILED, RETRYING, DEAD_LETTER
    progress = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error = Column(Text, nullable=True)
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    payload_json = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)
    idempotency_key = Column(String(128), nullable=True, index=True)
    locked_by = Column(String(128), nullable=True)
    locked_at = Column(DateTime, nullable=True)
    lease_expires_at = Column(DateTime, nullable=True, index=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_jobs_lease", "status", "lease_expires_at"),
    )


class SiteCredential(Base):
    """Encrypted Credential Storage in Database"""
    __tablename__ = "site_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    site_id = Column(String(128), nullable=False, index=True)
    key_name = Column(String(128), nullable=False)
    encrypted_value = Column(Text, nullable=False)
    key_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("site_id", "key_name", name="uq_site_credential_key"),
        Index("idx_site_cred_tenant", "tenant_id", "site_id"),
    )


class CloakedLink(Base):
    """Affiliate Cloaked Links"""
    __tablename__ = "cloaked_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    slug = Column(String(128), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    destination_url = Column(Text, nullable=False)
    target_country = Column(String(16), default="ALL")
    click_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ClickLog(Base):
    """Affiliate Link Click Logs"""
    __tablename__ = "click_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    link_id = Column(Integer, ForeignKey("cloaked_links.id", ondelete="CASCADE"), nullable=False)
    slug = Column(String(128))
    ip_hash = Column(String(64))
    referer = Column(Text)
    user_agent = Column(Text)
    clicked_at = Column(DateTime, default=datetime.utcnow)


class SentimentCache(Base):
    """Customer Review Analysis Cache"""
    __tablename__ = "sentiment_cache"

    asin = Column(String(64), primary_key=True)
    product_name = Column(String(255))
    complaints_json = Column(Text)
    praises_json = Column(Text)
    verified_quotes_json = Column(Text)
    rating = Column(Float)
    mined_at = Column(DateTime, default=datetime.utcnow)


class Article(Base):
    """Published and Draft Content"""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, default=1)
    site_id = Column(Integer, nullable=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=True)
    keyword = Column(String(255), nullable=False)
    asins = Column(Text, nullable=True)
    status = Column(String(32), default="draft")  # draft, publish, dry_run
    wp_post_id = Column(Integer, nullable=True)
    wp_link = Column(Text, nullable=True)
    eeat_score = Column(Integer, default=0)
    file_path = Column(Text, nullable=True)
    page_type = Column(String(32), default="review")
    primary_entity_id = Column(String(64), nullable=True)
    quality_score = Column(Float, nullable=True)
    quality_decision = Column(String(32), nullable=True)
    last_verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RankHistory(Base):
    """SERP Rank Tracking History"""
    __tablename__ = "rank_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, default=1)
    keyword = Column(String(255), nullable=False)
    domain = Column(String(128))
    rank_position = Column(Integer)
    status_message = Column(Text)
    checked_at = Column(DateTime, default=datetime.utcnow)


class CampaignPlan(Base):
    """Content Strategy Plans"""
    __tablename__ = "campaign_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, default=1)
    category_name = Column(String(128), nullable=False)
    category_url = Column(Text)
    total_items = Column(Integer, default=30)
    status = Column(String(32), default="ready")
    summary_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class ScheduledPost(Base):
    """Content Schedule Queue"""
    __tablename__ = "scheduled_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("campaign_plans.id", ondelete="CASCADE"), nullable=True)
    workspace_id = Column(Integer, default=1)
    site_id = Column(Integer, nullable=True)
    day_number = Column(Integer, nullable=False)
    publish_date = Column(String(32), nullable=False)
    article_type = Column(String(32), nullable=False)
    keyword = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    asins_json = Column(Text)
    status = Column(String(32), default="pending")
    wp_post_id = Column(Integer)
    wp_link = Column(Text)
    preview_file = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Entity(Base):
    """Canonical Real-World Domain Entity"""
    __tablename__ = "entities"

    id = Column(String(64), primary_key=True)
    project_id = Column(String(64), nullable=True)
    entity_type = Column(String(32), nullable=False)
    brand = Column(String(64), nullable=False)
    model = Column(String(128), nullable=False)
    sku_or_upc = Column(String(64), nullable=True)
    primary_image_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sources = relationship("Source", back_populates="entity", cascade="all, delete-orphan")
    attributes = relationship("EntityAttribute", back_populates="entity", cascade="all, delete-orphan")
    evidence_claims = relationship("EvidenceClaim", back_populates="entity", cascade="all, delete-orphan")
    merchant_offers = relationship("MerchantOffer", back_populates="entity", cascade="all, delete-orphan")


class Source(Base):
    """Ground-Truth Documentation & Manuals with Verifiable Provenance"""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(String(64), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    source_type = Column(String(32), nullable=False)  # oem_manual, official_spec, product_manufacturer, retailer, editorial, community
    priority = Column(Integer, default=3)  # 1=oem, 2=manual, 3=mfr, 4=retailer, 5=editorial, 6=community
    url = Column(Text, nullable=True)
    document_title = Column(Text, nullable=True)
    http_status = Column(Integer, default=200)
    content_hash = Column(String(64), nullable=True)
    parser_version = Column(String(16), default="1.0")
    is_stale = Column(Boolean, default=False)
    snapshot_archive_path = Column(Text, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    entity = relationship("Entity", back_populates="sources")
    evidence_claims = relationship("EvidenceClaim", back_populates="source", cascade="all, delete-orphan")


class EntityAttribute(Base):
    """Normalized Key-Value Technical Specifications"""
    __tablename__ = "entity_attributes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(String(64), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    attr_key = Column(String(64), nullable=False)
    attr_value_num = Column(Float, nullable=True)
    attr_value_text = Column(Text, nullable=True)
    unit = Column(String(16), nullable=True)
    confidence_score = Column(Float, default=1.0)
    verified_by_source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    is_unknown = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    entity = relationship("Entity", back_populates="attributes")

    __table_args__ = (
        Index("idx_entity_attr", "entity_id", "attr_key"),
    )


class EvidenceClaim(Base):
    """Granular Factual Quote Extracted from Source Document"""
    __tablename__ = "evidence_claims"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(String(64), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    attribute_key = Column(String(64), nullable=False)
    extracted_value = Column(Text, nullable=False)
    raw_quote = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    status = Column(String(16), default="VERIFIED")  # VERIFIED, STALE, CONFLICT
    created_at = Column(DateTime, default=datetime.utcnow)

    entity = relationship("Entity", back_populates="evidence_claims")
    source = relationship("Source", back_populates="evidence_claims")


class CompatibilityMatrix(Base):
    """Deterministic Physical & Electrical Compatibility Matrix"""
    __tablename__ = "compatibility_matrix"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_entity_id = Column(String(64), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    target_entity_id = Column(String(64), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    compatibility_status = Column(String(16), nullable=False)  # PASS, CONDITIONAL, FAIL
    fit_detail = Column(Text)
    max_clearance_inches = Column(Float)
    confidence = Column(Float, default=1.0)
    tested_method = Column(String(32), default="CALCULATED_DIMENSION")
    created_at = Column(DateTime, default=datetime.utcnow)


class MerchantOffer(Base):
    """Multi-Merchant Pricing & Affiliate Offers (Decoupled from Products)"""
    __tablename__ = "merchant_offers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(String(64), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    merchant_name = Column(String(32), nullable=False)  # Direct, Amazon, eBay
    external_id = Column(String(64), nullable=False)
    affiliate_url = Column(Text, nullable=False)
    current_price = Column(Float, nullable=True)
    currency = Column(String(8), default="USD")
    in_stock = Column(Boolean, default=True)
    offer_status = Column(String(16), default="ACTIVE")  # ACTIVE, OUT_OF_STOCK, EXPIRED, INVALID
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, default=0)
    last_checked_at = Column(DateTime, default=datetime.utcnow)

    entity = relationship("Entity", back_populates="merchant_offers")

    __table_args__ = (
        Index("idx_merchant_entity", "entity_id", "merchant_name"),
    )


class AttributeDefinition(Base):
    """Canonical Schema Specification for Technical Attributes"""
    __tablename__ = "attribute_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    attr_key = Column(String(64), unique=True, nullable=False)
    display_name = Column(String(128), nullable=False)
    data_type = Column(String(16), default="numeric")  # numeric, text, boolean
    default_unit = Column(String(16), nullable=True)
    description = Column(Text, nullable=True)


class EntityRelationship(Base):
    """Graph Topology of Entity Connections (fits_in, powers, compatible_with)"""
    __tablename__ = "entity_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(String(64), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    predicate = Column(String(64), nullable=False)
    object_id = Column(String(64), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    confidence = Column(Float, default=1.0)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_rel_subj_obj", "subject_id", "object_id"),
    )


class CalculationLog(Base):
    """Physics Calculation Audit Trail"""
    __tablename__ = "calculation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(String(64), nullable=True)
    calculation_type = Column(String(64), nullable=False)
    inputs_json = Column(Text, nullable=False)
    formula_version = Column(String(16), default="v1.0")
    assumptions_json = Column(Text, nullable=False)
    output_json = Column(Text, nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow)


class PagePlan(Base):
    """Content Strategy & Anti-Cannibalization Planning"""
    __tablename__ = "page_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, default=1)
    project_id = Column(String(64), nullable=True)
    target_keyword = Column(Text, nullable=False)
    intent_type = Column(String(32), nullable=False)  # informational, commercial, navigational
    cluster_id = Column(String(64), nullable=True)
    plan_action = Column(String(32), default="CREATE")  # CREATE, MERGE, UPDATE_EXISTING, NOINDEX, SKIP, RESEARCH_REQUIRED
    target_entity_ids = Column(Text, nullable=True)
    factual_brief_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PageQualityEvaluation(Base):
    """Quality Gate Audit Results with Hard Blockers"""
    __tablename__ = "page_quality_evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    page_plan_id = Column(Integer, ForeignKey("page_plans.id"), nullable=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=True)
    overall_score = Column(Float, nullable=False)
    status = Column(String(16), nullable=False)  # INDEX, NOINDEX, REVIEW, REJECT
    quality_breakdown_json = Column(Text, nullable=False)
    hard_blockers_json = Column(Text, default="[]")
    evaluated_at = Column(DateTime, default=datetime.utcnow)


class ClaimValidation(Base):
    """Fact-Checked Claims Mapped to Evidence Chains"""
    __tablename__ = "claim_validations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=True)
    claim_text = Column(Text, nullable=False)
    fact_id = Column(String(64), nullable=True)
    calculation_id = Column(Integer, nullable=True)
    evidence_id = Column(Integer, ForeignKey("evidence_claims.id"), nullable=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    validation_status = Column(String(16), nullable=False)  # VERIFIED, UNSUPPORTED, CONFLICT, FORBIDDEN
    matched_attribute_id = Column(Integer, ForeignKey("entity_attributes.id"), nullable=True)
    reason = Column(Text, nullable=True)
    validated_at = Column(DateTime, default=datetime.utcnow)


class GSCMetric(Base):
    """Google Search Console Daily Historical Query Records"""
    __tablename__ = "gsc_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, default=1)
    page_url = Column(Text, nullable=False)
    query = Column(Text, nullable=False)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    ctr = Column(Float, default=0.0)
    position = Column(Float, default=0.0)
    recorded_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_gsc_url_query", "page_url", "query"),
        Index("idx_gsc_date", "recorded_date"),
        UniqueConstraint("page_url", "query", "recorded_date", name="uq_gsc_url_query_date"),
    )


class AuditLog(Base):
    """System-Wide Observability & Audit Trail"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, default=1)
    action = Column(String(64), nullable=False)
    entity_type = Column(String(32), nullable=True)
    entity_id = Column(String(64), nullable=True)
    actor = Column(String(64), default="system")
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_audit_action", "action", "entity_id"),
    )


class InternalLink(Base):
    """Site-Wide Semantic Internal Link Topology"""
    __tablename__ = "internal_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workspace_id = Column(Integer, default=1)
    source_url = Column(Text, nullable=False)
    target_url = Column(Text, nullable=False)
    anchor_text = Column(String(255), nullable=False)
    anchor_type = Column(String(32), default="natural")  # brand_model, partial_match, natural
    context_snippet = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_internal_link_source", "source_url"),
        Index("idx_internal_link_target", "target_url"),
    )
