import sqlite3
import json
import hashlib
import secrets
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from core.config import settings

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "affiliate.db"

_engine = None
_SessionLocal = None

def get_engine():
    global _engine
    if _engine is None:
        url = settings.DATABASE_URL
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args)
    return _engine

def get_db_session() -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal()

def get_connection():
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
    return hashed, salt

def verify_password(password: str, hashed: str, salt: str) -> bool:
    check_hash = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
    return check_hash == hashed

def init_db():
    """Khởi tạo toàn bộ cấu trúc cơ sở dữ liệu Multi-Tenant SaaS & Data Authority Engine."""
    conn = get_connection()
    cursor = conn.cursor()

    # 0. Bảng Dự Án (Projects)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id VARCHAR(64) PRIMARY KEY,
        name VARCHAR(128) NOT NULL,
        niche VARCHAR(64) NOT NULL,
        target_country VARCHAR(16) DEFAULT 'US',
        config_json TEXT DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 1. Bảng Người Dùng (Users)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        full_name TEXT,
        plan_tier TEXT DEFAULT 'starter', -- 'free', 'starter', 'pro', 'agency'
        credits_remaining INTEGER DEFAULT 25,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. Bảng Không Gian Làm Việc (Workspaces)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS workspaces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        amazon_tag_us TEXT DEFAULT 'yourtag-20',
        amazon_tag_uk TEXT,
        amazon_tag_ca TEXT,
        amazon_tag_de TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # 3. Bảng Kết Nối Đa Website (Connected Sites)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS connected_sites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER NOT NULL,
        site_name TEXT NOT NULL,
        platform TEXT DEFAULT 'wordpress', -- 'wordpress', 'ghost', 'webhook'
        site_url TEXT NOT NULL,
        username TEXT NOT NULL,
        app_password TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
    )
    """)

    # 4. Bảng Hàng Đợi Tác Vụ Ngầm (Background Jobs)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        workspace_id INTEGER NOT NULL DEFAULT 1,
        project_id VARCHAR(64),
        job_type VARCHAR(64) DEFAULT 'generic',
        task_type TEXT DEFAULT 'generic',
        status TEXT DEFAULT 'QUEUED',
        progress INTEGER DEFAULT 0,
        retry_count INTEGER DEFAULT 0,
        input_summary TEXT,
        output_summary TEXT,
        result_json TEXT,
        error_msg TEXT,
        error TEXT,
        started_at TIMESTAMP,
        finished_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP
    )
    """)

    # 5. Bảng Link Bọc & Đo Lường Click (Cloaked Links)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cloaked_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        destination_url TEXT NOT NULL,
        target_country TEXT DEFAULT 'ALL',
        click_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
    )
    """)

    # 5b. Bảng Lịch Sử Click Chi Tiết (Click Logs for Analytics)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS click_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        link_id INTEGER NOT NULL,
        slug TEXT,
        ip_hash TEXT,
        referer TEXT,
        user_agent TEXT,
        clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(link_id) REFERENCES cloaked_links(id) ON DELETE CASCADE
    )
    """)

    # 6. Bảng Phân Tích Cảm Xúc Review Khách Hàng (Sentiment Cache)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sentiment_cache (
        asin TEXT PRIMARY KEY,
        product_name TEXT,
        complaints_json TEXT, -- Những lời phàn nàn thực tế
        praises_json TEXT,    -- Những điểm được khen ngợi
        verified_quotes_json TEXT, -- Trích dẫn nguyên văn của khách hàng thật
        rating REAL,
        mined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 7. Bảng Bài Viết (Articles - Multi-Tenant)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER DEFAULT 1,
        site_id INTEGER,
        title TEXT NOT NULL,
        slug TEXT,
        keyword TEXT NOT NULL,
        asins TEXT,
        status TEXT, -- 'draft', 'publish', 'dry_run'
        wp_post_id INTEGER,
        wp_link TEXT,
        eeat_score INTEGER DEFAULT 0,
        file_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 8. Bảng Thứ Hạng SERP (Rank Tracking)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rank_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER DEFAULT 1,
        keyword TEXT NOT NULL,
        domain TEXT,
        rank_position INTEGER,
        status_message TEXT,
        checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 9. Bảng Kế Hoạch Chiến Dịch 30 Ngày (Campaign Plans)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS campaign_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER DEFAULT 1,
        category_name TEXT NOT NULL,
        category_url TEXT,
        total_items INTEGER DEFAULT 30,
        status TEXT DEFAULT 'ready', -- 'analyzing', 'ready', 'scheduling', 'completed'
        summary_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 10. Bảng Lịch Đăng Bài 30 Ngày Tự Động (Scheduled Posts Calendar)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scheduled_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER,
        workspace_id INTEGER DEFAULT 1,
        site_id INTEGER,
        day_number INTEGER NOT NULL,
        publish_date TEXT NOT NULL,
        article_type TEXT NOT NULL, -- 'roundup', 'single', 'vs', 'how_to'
        keyword TEXT NOT NULL,
        title TEXT NOT NULL,
        asins_json TEXT,
        status TEXT DEFAULT 'pending', -- 'pending', 'generating', 'scheduled', 'published', 'failed'
        wp_post_id INTEGER,
        wp_link TEXT,
        preview_file TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(plan_id) REFERENCES campaign_plans(id) ON DELETE CASCADE
    )
    """)

    # 13. Bảng Thực Thể (Generic Product / Vehicle / Gear Entity)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS entities (
        id VARCHAR(64) PRIMARY KEY,
        entity_type VARCHAR(32) NOT NULL,
        brand VARCHAR(64) NOT NULL,
        model VARCHAR(128) NOT NULL,
        sku_or_upc VARCHAR(64),
        primary_image_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 14. Bảng Nguồn Dữ Liệu Thực Tế (Source Authority & Documentation)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id VARCHAR(64) NOT NULL,
        source_type VARCHAR(32) NOT NULL,
        url TEXT,
        document_title TEXT,
        snapshot_archive_path TEXT,
        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(entity_id) REFERENCES entities(id) ON DELETE CASCADE
    )
    """)

    # 15. Bảng Thuộc Tính Kỹ Thuật Chuẩn Hóa (Normalized Specifications)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS entity_attributes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id VARCHAR(64) NOT NULL,
        attr_key VARCHAR(64) NOT NULL,
        attr_value_num REAL,
        attr_value_text TEXT,
        unit VARCHAR(16),
        confidence_score REAL DEFAULT 1.0,
        verified_by_source_id INTEGER,
        FOREIGN KEY(entity_id) REFERENCES entities(id) ON DELETE CASCADE,
        FOREIGN KEY(verified_by_source_id) REFERENCES sources(id)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_attr ON entity_attributes(entity_id, attr_key)")

    # 16. Bảng Bằng Chứng & Trích Dẫn (Evidence Claims)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evidence_claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id VARCHAR(64) NOT NULL,
        source_id INTEGER NOT NULL,
        attribute_key VARCHAR(64) NOT NULL,
        extracted_value TEXT NOT NULL,
        raw_quote TEXT NOT NULL,
        page_number INTEGER,
        status VARCHAR(16) DEFAULT 'VERIFIED',
        FOREIGN KEY(entity_id) REFERENCES entities(id) ON DELETE CASCADE,
        FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
    )
    """)

    # 17. Bảng Ma Trận Tương Thích (Compatibility Matrix)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS compatibility_matrix (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_entity_id VARCHAR(64) NOT NULL,
        target_entity_id VARCHAR(64) NOT NULL,
        compatibility_status VARCHAR(16) NOT NULL,
        fit_detail TEXT,
        max_clearance_inches REAL,
        tested_method VARCHAR(32) DEFAULT 'CALCULATED_DIMENSION',
        FOREIGN KEY(subject_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
        FOREIGN KEY(target_entity_id) REFERENCES entities(id) ON DELETE CASCADE
    )
    """)

    # 18. Bảng Ưu Đãi Thương Mại Động (Dynamic Merchant Offers)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS merchant_offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id VARCHAR(64) NOT NULL,
        merchant_name VARCHAR(32) NOT NULL,
        external_id VARCHAR(64) NOT NULL,
        affiliate_url TEXT NOT NULL,
        current_price REAL,
        currency VARCHAR(8) DEFAULT 'USD',
        in_stock BOOLEAN DEFAULT 1,
        rating REAL,
        review_count INTEGER,
        last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(entity_id) REFERENCES entities(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_merchant_entity ON merchant_offers(entity_id, merchant_name)")

    # 19. Bảng Định Nghĩa Thuộc Tính Chuẩn (Attribute Definitions)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attribute_definitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attr_key VARCHAR(64) UNIQUE NOT NULL,
        display_name VARCHAR(128) NOT NULL,
        data_type VARCHAR(16) DEFAULT 'numeric', -- 'numeric', 'text', 'boolean'
        default_unit VARCHAR(16),
        description TEXT
    )
    """)

    # 20. Bảng Quan Hệ Thực Thể (Entity Relationships)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS entity_relationships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id VARCHAR(64) NOT NULL,
        predicate VARCHAR(64) NOT NULL, -- 'fits_in', 'powers', 'compatible_with'
        object_id VARCHAR(64) NOT NULL,
        confidence REAL DEFAULT 1.0,
        source_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(subject_id) REFERENCES entities(id) ON DELETE CASCADE,
        FOREIGN KEY(object_id) REFERENCES entities(id) ON DELETE CASCADE,
        FOREIGN KEY(source_id) REFERENCES sources(id)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_subj_obj ON entity_relationships(subject_id, object_id)")

    # 21. Bảng Nhật Ký Tính Toán Vật Lý (Deterministic Calculation Logs)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS calculation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id VARCHAR(64),
        calculation_type VARCHAR(64) NOT NULL, -- 'power_runtime', 'fridge_runtime', 'cargo_fitment'
        inputs_json TEXT NOT NULL,
        formula_version VARCHAR(16) DEFAULT 'v1.0',
        assumptions_json TEXT NOT NULL,
        output_json TEXT NOT NULL,
        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 22. Bảng Kế Hoạch Trang & Intent Clustering (Page Plans)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS page_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER DEFAULT 1,
        target_keyword TEXT NOT NULL,
        intent_type VARCHAR(32) NOT NULL, -- 'informational', 'commercial', 'navigational'
        cluster_id VARCHAR(64),
        plan_action VARCHAR(32) DEFAULT 'CREATE', -- 'CREATE', 'MERGE', 'UPDATE_EXISTING', 'NOINDEX', 'SKIP'
        target_entity_ids TEXT,
        factual_brief_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 23. Bảng Đánh Giá Chất Lượng Trang (Page Quality Evaluations)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS page_quality_evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page_plan_id INTEGER,
        article_id INTEGER,
        overall_score REAL NOT NULL,
        status VARCHAR(16) NOT NULL, -- 'PASSED', 'REJECTED', 'NEEDS_REVIEW'
        quality_breakdown_json TEXT NOT NULL,
        evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(page_plan_id) REFERENCES page_plans(id),
        FOREIGN KEY(article_id) REFERENCES articles(id)
    )
    """)

    # 24. Bảng Xác Thực Luận Điểm Dẫn Chứng (Claim Validations)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS claim_validations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER,
        claim_text TEXT NOT NULL,
        validation_status VARCHAR(16) NOT NULL, -- 'VERIFIED', 'UNSUPPORTED', 'CONFLICT', 'FORBIDDEN'
        matched_attribute_id INTEGER,
        reason TEXT,
        validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(article_id) REFERENCES articles(id),
        FOREIGN KEY(matched_attribute_id) REFERENCES entity_attributes(id)
    )
    """)

    # 25. Bảng Dữ Liệu Google Search Console (GSC Metrics)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS gsc_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER DEFAULT 1,
        page_url TEXT NOT NULL,
        query TEXT NOT NULL,
        impressions INTEGER DEFAULT 0,
        clicks INTEGER DEFAULT 0,
        ctr REAL DEFAULT 0.0,
        position REAL DEFAULT 0.0,
        recorded_date DATE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gsc_url_query ON gsc_metrics(page_url, query)")

    # 26. Bảng Nhật Ký Kiểm Toán Toàn Hệ Thống (Audit Logs)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER DEFAULT 1,
        action VARCHAR(64) NOT NULL,
        entity_type VARCHAR(32),
        entity_id VARCHAR(64),
        actor VARCHAR(64) DEFAULT 'system',
        details_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action, entity_id)")

    # 27. Bảng Liên Kết Nội Bộ (Internal Links)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS internal_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER DEFAULT 1,
        source_url TEXT NOT NULL,
        target_url TEXT NOT NULL,
        anchor_text VARCHAR(255) NOT NULL,
        anchor_type VARCHAR(32) DEFAULT 'natural',
        context_snippet TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_internal_link_source ON internal_links(source_url)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_internal_link_target ON internal_links(target_url)")

    # 28. Bảng SERP Snapshots & Competitor Intelligence (SERP Snapshots)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS serp_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT NOT NULL,
        market VARCHAR(16) DEFAULT 'US',
        language VARCHAR(16) DEFAULT 'en',
        device VARCHAR(16) DEFAULT 'desktop',
        volume_label VARCHAR(16) DEFAULT 'ESTIMATED', -- 'REAL', 'ESTIMATED', 'HEURISTIC', 'UNKNOWN'
        estimated_volume INTEGER DEFAULT 0,
        top_results_json TEXT NOT NULL, -- JSON list of rank, url, domain, title, result_type, page_type
        serp_gap_json TEXT, -- JSON of intent_gap, exact_answer_gap, data_gap, etc.
        opportunity_score REAL DEFAULT 0.0,
        opportunity_breakdown_json TEXT,
        evidence_readiness VARCHAR(32) DEFAULT 'RESEARCH_REQUIRED', -- 'READY', 'PARTIAL', 'RESEARCH_REQUIRED', 'BLOCKED'
        retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_serp_query ON serp_snapshots(query)")


    # Tự động migrate thêm cột nếu bảng đã tồn tại từ trước
    schema_patches = [
        ("workspace_id", "articles", "INTEGER DEFAULT 1"),
        ("site_id", "articles", "INTEGER"),
        ("page_type", "articles", "VARCHAR(32) DEFAULT 'review'"),
        ("primary_entity_id", "articles", "VARCHAR(64)"),
        ("quality_score", "articles", "REAL"),
        ("quality_decision", "articles", "VARCHAR(32)"),
        ("last_verified_at", "articles", "TIMESTAMP"),
        ("workspace_id", "rank_history", "INTEGER DEFAULT 1"),
        ("project_id", "page_plans", "VARCHAR(64)"),
        ("project_id", "entities", "VARCHAR(64)"),
        ("priority", "sources", "INTEGER DEFAULT 3"),
        ("http_status", "sources", "INTEGER DEFAULT 200"),
        ("content_hash", "sources", "VARCHAR(64)"),
        ("parser_version", "sources", "VARCHAR(16) DEFAULT '1.0'"),
        ("is_stale", "sources", "BOOLEAN DEFAULT 0"),
        ("offer_status", "merchant_offers", "VARCHAR(16) DEFAULT 'ACTIVE'"),
        ("hard_blockers_json", "page_quality_evaluations", "TEXT DEFAULT '[]'"),
        ("fact_id", "claim_validations", "VARCHAR(64)"),
        ("calculation_id", "claim_validations", "INTEGER"),
        ("evidence_id", "claim_validations", "INTEGER"),
        ("source_id", "claim_validations", "INTEGER"),
        ("created_at", "evidence_claims", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("project_id", "jobs", "VARCHAR(64)"),
        ("job_type", "jobs", "VARCHAR(64) DEFAULT 'generic'"),
        ("retry_count", "jobs", "INTEGER DEFAULT 0"),
        ("input_summary", "jobs", "TEXT"),
        ("output_summary", "jobs", "TEXT"),
        ("started_at", "jobs", "TIMESTAMP"),
        ("finished_at", "jobs", "TIMESTAMP"),
        ("freshness_policy", "attribute_definitions", "VARCHAR(32) DEFAULT 'SEMI_DYNAMIC'"),
        ("refresh_interval_days", "attribute_definitions", "INTEGER DEFAULT 180"),
        ("invalidate_on_source_change", "attribute_definitions", "INTEGER DEFAULT 1"),
    ]
    for col, tbl, col_type in schema_patches:
        try:
            cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass

    # Tạo User Admin Mặc định nếu chưa có
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        pw_hash, salt = hash_password("admin123")
        cursor.execute("""
        INSERT INTO users (email, password_hash, salt, full_name, plan_tier, credits_remaining)
        VALUES (?, ?, ?, ?, ?, ?)
        """, ("admin@openseo.local", pw_hash, salt, "SaaS SuperAdmin", "agency", 500))
        user_id = cursor.lastrowid

        # Workspace mặc định
        cursor.execute("""
        INSERT INTO workspaces (user_id, name, amazon_tag_us)
        VALUES (?, ?, ?)
        """, (user_id, "Default Affiliate Workspace", "yourstore-20"))
        ws_id = cursor.lastrowid

        # Site mặc định (nếu có trong .env)
        cursor.execute("""
        INSERT INTO connected_sites (workspace_id, site_name, site_url, username, app_password)
        VALUES (?, ?, ?, ?, ?)
        """, (ws_id, "Primary Affiliate Site", "https://your-affiliate-website.com", "admin", "xxxx xxxx xxxx xxxx"))

    conn.commit()
    conn.close()

# Helper Functions
def create_project(project_id: str, name: str, niche: str, target_country: str = "US", config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    config_str = json.dumps(config or {})
    cursor.execute("""
    INSERT OR REPLACE INTO projects (id, name, niche, target_country, config_json, updated_at)
    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (project_id, name, niche, target_country, config_str))
    conn.commit()
    conn.close()
    return {"id": project_id, "name": name, "niche": niche, "target_country": target_country, "config": config or {}}

def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        try:
            d["config"] = json.loads(d.get("config_json") or "{}")
        except:
            d["config"] = {}
        return d
    return None

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(email: str, password: str, full_name: str = "") -> Dict[str, Any]:
    email = email.strip().lower()
    pw_hash, salt = hash_password(password)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO users (email, password_hash, salt, full_name, plan_tier, credits_remaining)
    VALUES (?, ?, ?, ?, 'starter', 25)
    """, (email, pw_hash, salt, full_name))
    new_user_id = cursor.lastrowid
    
    # Tạo workspace mặc định
    cursor.execute("""
    INSERT INTO workspaces (user_id, name, amazon_tag_us)
    VALUES (?, ?, ?)
    """, (new_user_id, f"Workspace của {full_name or email}", "affiliate-20"))
    
    conn.commit()
    conn.close()
    return {"id": new_user_id, "email": email, "full_name": full_name, "credits": 25}

def get_workspace_for_user(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM workspaces WHERE user_id = ? LIMIT 1", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_workspaces_for_user(user_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT w.*, COUNT(s.id) as site_count 
    FROM workspaces w 
    LEFT JOIN connected_sites s ON w.id = s.workspace_id 
    WHERE w.user_id = ? 
    GROUP BY w.id 
    ORDER BY w.id ASC
    """, (user_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def create_workspace(user_id: int, name: str, amazon_tag_us: str = "yourtag-20") -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO workspaces (user_id, name, amazon_tag_us)
    VALUES (?, ?, ?)
    """, (user_id, name.strip(), amazon_tag_us.strip()))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": new_id, "user_id": user_id, "name": name, "amazon_tag_us": amazon_tag_us}

def delete_workspace(workspace_id: int, user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM workspaces WHERE id = ? AND user_id = ?", (workspace_id, user_id))
    conn.commit()
    conn.close()
    return True

def deduct_credit(user_id: int, amount: int = 1) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT credits_remaining FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if not row or row[0] < amount:
        conn.close()
        return False
    cursor.execute("UPDATE users SET credits_remaining = credits_remaining - ? WHERE id = ?", (amount, user_id))
    conn.commit()
    conn.close()
    return True

def save_article_record(
    title: str,
    slug: str,
    keyword: str,
    asins: List[str],
    status: str = "draft",
    wp_post_id: Optional[int] = None,
    wp_link: Optional[str] = None,
    eeat_score: int = 0,
    file_path: Optional[str] = None,
    workspace_id: int = 1
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO articles (workspace_id, title, slug, keyword, asins, status, wp_post_id, wp_link, eeat_score, file_path)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        workspace_id,
        title,
        slug,
        keyword,
        ",".join(asins) if isinstance(asins, list) else str(asins),
        status,
        wp_post_id,
        wp_link,
        eeat_score,
        file_path
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def get_recent_articles(limit: int = 15, workspace_id: int = 1) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT id, title, slug, keyword, asins, status, wp_post_id, wp_link, eeat_score, file_path, created_at
        FROM articles
        WHERE workspace_id = ?
        ORDER BY id DESC
        LIMIT ?
        """, (workspace_id, limit))
    except Exception:
        cursor.execute("""
        SELECT id, title, slug, keyword, asins, status, wp_post_id, wp_link, eeat_score, file_path, created_at
        FROM articles
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_rank_record(keyword: str, domain: str, rank: Optional[int], status_message: str = "", workspace_id: int = 1) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO rank_history (workspace_id, keyword, domain, rank_position, status_message)
    VALUES (?, ?, ?, ?, ?)
    """, (workspace_id, keyword, domain, rank, status_message))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def get_db_stats(workspace_id: int = 1) -> Dict[str, int]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM articles WHERE workspace_id = ?", (workspace_id,))
        total_articles = cursor.fetchone()[0]
    except Exception:
        cursor.execute("SELECT COUNT(*) FROM articles")
        total_articles = cursor.fetchone()[0]

    try:
        cursor.execute("SELECT COUNT(*) FROM articles WHERE workspace_id = ? AND status = 'publish'", (workspace_id,))
        published_articles = cursor.fetchone()[0]
    except Exception:
        cursor.execute("SELECT COUNT(*) FROM articles WHERE status = 'publish'")
        published_articles = cursor.fetchone()[0]

    try:
        cursor.execute("SELECT COUNT(*) FROM rank_history WHERE workspace_id = ?", (workspace_id,))
        tracked_ranks = cursor.fetchone()[0]
    except Exception:
        cursor.execute("SELECT COUNT(*) FROM rank_history")
        tracked_ranks = cursor.fetchone()[0]

    conn.close()
    return {
        "total_articles": total_articles,
        "published_articles": published_articles,
        "tracked_ranks": tracked_ranks
    }

# ----------------- Campaign Plans & 30-Day Calendar -----------------
def create_campaign_plan(category_name: str, category_url: str = "", total_items: int = 30, summary: Dict[str, Any] = None, workspace_id: int = 1) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO campaign_plans (workspace_id, category_name, category_url, total_items, status, summary_json)
    VALUES (?, ?, ?, ?, 'ready', ?)
    """, (workspace_id, category_name, category_url, total_items, json.dumps(summary or {}, ensure_ascii=False)))
    plan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return plan_id

def save_scheduled_posts(plan_id: int, posts: List[Dict[str, Any]], workspace_id: int = 1):
    conn = get_connection()
    cursor = conn.cursor()
    for p in posts:
        asins_str = json.dumps(p.get("asins", []), ensure_ascii=False)
        cursor.execute("""
        INSERT INTO scheduled_posts (
            plan_id, workspace_id, site_id, day_number, publish_date, 
            article_type, keyword, title, asins_json, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            plan_id, workspace_id, p.get("site_id"), p.get("day_number", 1), p.get("publish_date", ""),
            p.get("article_type", "roundup"), p.get("keyword", ""), p.get("title", ""), asins_str,
            p.get("status", "pending")
        ))
    conn.commit()
    conn.close()

def get_campaign_plan(plan_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM campaign_plans WHERE id = ?", (plan_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    data = dict(row)
    if data.get("summary_json"):
        try:
            data["summary"] = json.loads(data["summary_json"])
        except Exception:
            data["summary"] = {}

    cursor.execute("SELECT * FROM scheduled_posts WHERE plan_id = ? ORDER BY day_number ASC", (plan_id,))
    post_rows = cursor.fetchall()
    posts = []
    for pr in post_rows:
        pdict = dict(pr)
        if pdict.get("asins_json"):
            try:
                pdict["asins"] = json.loads(pdict["asins_json"])
            except Exception:
                pdict["asins"] = []
        posts.append(pdict)
    data["posts"] = posts
    conn.close()
    return data

def list_campaign_plans(workspace_id: int = 1) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM campaign_plans WHERE workspace_id = ? ORDER BY id DESC", (workspace_id,))
    rows = cursor.fetchall()
    plans = []
    for r in rows:
        d = dict(r)
        if d.get("summary_json"):
            try:
                d["summary"] = json.loads(d["summary_json"])
            except Exception:
                d["summary"] = {}
        plans.append(d)
    conn.close()
    return plans

def update_scheduled_post_status(post_id: int, status: str, wp_post_id: Optional[int] = None, wp_link: Optional[str] = None, preview_file: Optional[str] = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE scheduled_posts
    SET status = ?, wp_post_id = COALESCE(?, wp_post_id), wp_link = COALESCE(?, wp_link), preview_file = COALESCE(?, preview_file)
    WHERE id = ?
    """, (status, wp_post_id, wp_link, preview_file, post_id))
    conn.commit()
    conn.close()

def update_scheduled_post_keyword(plan_id: int, day_number: int, keyword: str, title: str, article_type: str, asins: List[str]):
    """Cập nhật từ khóa và tiêu đề của một ngày trong kế hoạch biên tập."""
    conn = get_connection()
    cursor = conn.cursor()
    asins_str = json.dumps(asins or [], ensure_ascii=False)
    cursor.execute("""
    UPDATE scheduled_posts
    SET keyword = ?, title = ?, article_type = ?, asins_json = ?
    WHERE plan_id = ? AND day_number = ?
    """, (keyword, title, article_type, asins_str, plan_id, day_number))
    conn.commit()
    conn.close()

def get_used_keywords(workspace_id: int = 1) -> set:
    """Truy vấn toàn bộ các từ khóa đã từng được đưa vào kế hoạch hoặc đã xuất bản để tránh trùng lặp."""
    conn = get_connection()
    cursor = conn.cursor()
    used = set()
    try:
        cursor.execute("SELECT keyword FROM scheduled_posts WHERE workspace_id = ?", (workspace_id,))
        for r in cursor.fetchall():
            if r[0]:
                used.add(r[0].strip().lower())
    except Exception:
        pass
    try:
        cursor.execute("SELECT keyword FROM articles WHERE workspace_id = ?", (workspace_id,))
        for r in cursor.fetchall():
            if r[0]:
                used.add(r[0].strip().lower())
    except Exception:
        pass
    conn.close()
    return used

def get_keyword_content_repository(workspace_id: int = 1) -> Dict[str, Any]:
    """
    Truy vấn kho lưu trữ tổng hợp toàn diện:
    - Danh sách từ khóa đã quét / đã lưu từ tất cả các Campaign Plan.
    - Trạng thái bài viết: Đã xuất bản lên website nào (kèm link), Đang lên lịch, hay Chưa dùng.
    - Thống kê tổng hợp số lượng từ khóa, số bài đã publish, số site đã kết nối.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Lấy danh sách website
    sites_map = {}
    try:
        cursor.execute("SELECT id, site_name, site_url FROM connected_sites WHERE workspace_id = ?", (workspace_id,))
        for s in cursor.fetchall():
            sites_map[s["id"]] = {"name": s["site_name"], "url": s["site_url"]}
    except Exception:
        pass

    # 2. Lấy các bài viết đã xuất bản / draft từ bảng articles
    articles_by_kw = {}
    try:
        cursor.execute("""
            SELECT id, site_id, title, keyword, status, wp_post_id, wp_link, file_path, created_at 
            FROM articles 
            WHERE workspace_id = ? 
            ORDER BY id DESC
        """, (workspace_id,))
        for a in cursor.fetchall():
            kw_clean = (a["keyword"] or "").strip().lower()
            if kw_clean and kw_clean not in articles_by_kw:
                site_info = sites_map.get(a["site_id"], {"name": "WordPress Site", "url": ""})
                articles_by_kw[kw_clean] = {
                    "article_id": a["id"],
                    "title": a["title"],
                    "status": a["status"] or "published",
                    "wp_post_id": a["wp_post_id"],
                    "wp_link": a["wp_link"],
                    "file_path": a["file_path"],
                    "site_name": site_info["name"],
                    "site_url": site_info["url"],
                    "published_at": a["created_at"]
                }
    except Exception:
        pass

    # 3. Lấy các bài viết trong lịch scheduled_posts
    scheduled_by_kw = {}
    try:
        cursor.execute("""
            SELECT id, plan_id, site_id, day_number, publish_date, article_type, keyword, title, status, wp_post_id, wp_link, preview_file, created_at 
            FROM scheduled_posts 
            WHERE workspace_id = ? 
            ORDER BY id DESC
        """, (workspace_id,))
        for sp in cursor.fetchall():
            kw_clean = (sp["keyword"] or "").strip().lower()
            if kw_clean and kw_clean not in scheduled_by_kw:
                site_info = sites_map.get(sp["site_id"], {"name": "WordPress Site", "url": ""})
                scheduled_by_kw[kw_clean] = {
                    "scheduled_id": sp["id"],
                    "plan_id": sp["plan_id"],
                    "day_number": sp["day_number"],
                    "title": sp["title"],
                    "article_type": sp["article_type"],
                    "status": sp["status"] or "scheduled",
                    "wp_post_id": sp["wp_post_id"],
                    "wp_link": sp["wp_link"],
                    "preview_file": sp["preview_file"],
                    "site_name": site_info["name"],
                    "site_url": site_info["url"],
                    "publish_date": sp["publish_date"]
                }
    except Exception:
        pass

    # 4. Trích xuất từ khóa từ tất cả các Campaign Plans
    keywords_list = []
    seen_kw = set()

    try:
        cursor.execute("SELECT id, category_name, summary_json, created_at FROM campaign_plans WHERE workspace_id = ? ORDER BY id DESC", (workspace_id,))
        for p in cursor.fetchall():
            cat = p["category_name"]
            plan_id = p["id"]
            created_at = p["created_at"]
            if p["summary_json"]:
                try:
                    summary = json.loads(p["summary_json"])
                    all_diamonds = summary.get("all_diamonds", []) or summary.get("top_diamonds", [])
                    for kw_item in all_diamonds:
                        raw_k = kw_item.get("keyword", "").strip()
                        k_lower = raw_k.lower()
                        if not raw_k or k_lower in seen_kw:
                            continue
                        seen_kw.add(k_lower)

                        # Xác định trạng thái
                        status = "unused"
                        article_data = None
                        if k_lower in articles_by_kw:
                            status = "published"
                            article_data = articles_by_kw[k_lower]
                        elif k_lower in scheduled_by_kw:
                            sp_data = scheduled_by_kw[k_lower]
                            status = "published" if sp_data.get("wp_post_id") else "scheduled"
                            article_data = sp_data

                        keywords_list.append({
                            "keyword": raw_k,
                            "category": cat,
                            "volume": kw_item.get("volume", 2500),
                            "kd": kw_item.get("kd", 20),
                            "diamond_score": kw_item.get("diamond_score", 90),
                            "intent": kw_item.get("intent", "🛒 Buyer Roundup"),
                            "badge": kw_item.get("badge", "💎 Kim Cương"),
                            "status": status,
                            "article": article_data,
                            "plan_id": plan_id,
                            "scanned_at": created_at
                        })
                except Exception:
                    pass
    except Exception:
        pass

    # Bổ sung các từ khóa đã có trong articles mà chưa có trong plans
    for k_lower, art in articles_by_kw.items():
        if k_lower not in seen_kw:
            seen_kw.add(k_lower)
            keywords_list.append({
                "keyword": art.get("title", k_lower),
                "category": "Affiliate Content",
                "volume": 3200,
                "kd": 18,
                "diamond_score": 92,
                "intent": "🛒 Đã Xuất Bản",
                "badge": "💎 Kim Cương",
                "status": "published",
                "article": art,
                "plan_id": None,
                "scanned_at": art.get("published_at")
            })

    conn.close()

    total_kw = len(keywords_list)
    published_count = sum(1 for k in keywords_list if k["status"] == "published")
    scheduled_count = sum(1 for k in keywords_list if k["status"] == "scheduled")
    unused_count = sum(1 for k in keywords_list if k["status"] == "unused")

    return {
        "success": True,
        "total_keywords": total_kw,
        "published_count": published_count,
        "scheduled_count": scheduled_count,
        "unused_count": unused_count,
        "keywords": keywords_list
    }

# ==============================================================================
# DATA AUTHORITY ENTITY & EVIDENCE HELPERS
# ==============================================================================

def upsert_entity(entity_id: str, entity_type: str, brand: str, model: str, sku_or_upc: Optional[str] = None, primary_image_url: Optional[str] = None) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO entities (id, entity_type, brand, model, sku_or_upc, primary_image_url, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(id) DO UPDATE SET
        entity_type=excluded.entity_type,
        brand=excluded.brand,
        model=excluded.model,
        sku_or_upc=COALESCE(excluded.sku_or_upc, entities.sku_or_upc),
        primary_image_url=COALESCE(excluded.primary_image_url, entities.primary_image_url),
        updated_at=CURRENT_TIMESTAMP
    """, (entity_id, entity_type, brand, model, sku_or_upc, primary_image_url))
    conn.commit()
    conn.close()
    return get_entity(entity_id)

def get_entity(entity_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entities WHERE id = ?", (entity_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    entity = dict(row)
    # Gắn thêm attributes, offers và sources
    cursor.execute("SELECT * FROM entity_attributes WHERE entity_id = ?", (entity_id,))
    entity["attributes"] = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM merchant_offers WHERE entity_id = ?", (entity_id,))
    entity["merchant_offers"] = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM sources WHERE entity_id = ?", (entity_id,))
    entity["sources"] = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return entity

def list_entities(entity_type: Optional[str] = None, search: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM entities WHERE 1=1"
    params = []
    if entity_type:
        query += " AND entity_type = ?"
        params.append(entity_type)
    if search:
        query += " AND (brand LIKE ? OR model LIKE ? OR id LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])
    query += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    results = []
    for r in rows:
        ent = dict(r)
        # lấy số lượng verified attributes
        cursor.execute("SELECT COUNT(*) FROM entity_attributes WHERE entity_id = ?", (ent["id"],))
        ent["attr_count"] = cursor.fetchone()[0]
        results.append(ent)
    conn.close()
    return results

def upsert_entity_attribute(entity_id: str, attr_key: str, attr_value_num: Optional[float] = None, attr_value_text: Optional[str] = None, unit: Optional[str] = None, confidence_score: float = 1.0, verified_by_source_id: Optional[int] = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM entity_attributes WHERE entity_id = ? AND attr_key = ?", (entity_id, attr_key))
    cursor.execute("""
    INSERT INTO entity_attributes (entity_id, attr_key, attr_value_num, attr_value_text, unit, confidence_score, verified_by_source_id)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (entity_id, attr_key, attr_value_num, attr_value_text, unit, confidence_score, verified_by_source_id))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def get_entity_attributes(entity_id: str) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entity_attributes WHERE entity_id = ?", (entity_id,))
    attrs = {}
    for r in cursor.fetchall():
        d = dict(r)
        attrs[d["attr_key"]] = {
            "num": d["attr_value_num"],
            "text": d["attr_value_text"],
            "unit": d["unit"],
            "confidence": d["confidence_score"],
            "source_id": d["verified_by_source_id"]
        }
    conn.close()
    return attrs

def add_source(entity_id: str, source_type: str, url: Optional[str] = None, document_title: Optional[str] = None, snapshot_archive_path: Optional[str] = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO sources (entity_id, source_type, url, document_title, snapshot_archive_path)
    VALUES (?, ?, ?, ?, ?)
    """, (entity_id, source_type, url, document_title, snapshot_archive_path))
    s_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return s_id

def add_evidence_claim(entity_id: str, source_id: int, attribute_key: str, extracted_value: str, raw_quote: str, page_number: Optional[int] = None, status: str = 'VERIFIED') -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO evidence_claims (entity_id, source_id, attribute_key, extracted_value, raw_quote, page_number, status)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (entity_id, source_id, attribute_key, extracted_value, raw_quote, page_number, status))
    cid = cursor.lastrowid
    conn.commit()
    conn.close()
    return cid

def get_evidence_claims(entity_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT ec.*, s.source_type, s.document_title, s.url 
    FROM evidence_claims ec
    JOIN sources s ON ec.source_id = s.id
    WHERE ec.entity_id = ?
    ORDER BY ec.id DESC
    """, (entity_id,))
    claims = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return claims

def upsert_compatibility(subject_entity_id: str, target_entity_id: str, compatibility_status: str, fit_detail: Optional[str] = None, max_clearance_inches: Optional[float] = None, tested_method: str = 'CALCULATED_DIMENSION') -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    DELETE FROM compatibility_matrix 
    WHERE subject_entity_id = ? AND target_entity_id = ?
    """, (subject_entity_id, target_entity_id))
    cursor.execute("""
    INSERT INTO compatibility_matrix (subject_entity_id, target_entity_id, compatibility_status, fit_detail, max_clearance_inches, tested_method)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (subject_entity_id, target_entity_id, compatibility_status, fit_detail, max_clearance_inches, tested_method))
    cid = cursor.lastrowid
    conn.commit()
    conn.close()
    return cid

def get_compatibility(subject_entity_id: str, target_entity_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if target_entity_id:
        cursor.execute("SELECT * FROM compatibility_matrix WHERE subject_entity_id = ? AND target_entity_id = ?", (subject_entity_id, target_entity_id))
    else:
        cursor.execute("SELECT * FROM compatibility_matrix WHERE subject_entity_id = ? OR target_entity_id = ?", (subject_entity_id, subject_entity_id))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def upsert_merchant_offer(entity_id: str, merchant_name: str, external_id: str, affiliate_url: str, current_price: Optional[float] = None, currency: str = 'USD', in_stock: bool = True, rating: Optional[float] = None, review_count: Optional[int] = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    DELETE FROM merchant_offers 
    WHERE entity_id = ? AND merchant_name = ? AND external_id = ?
    """, (entity_id, merchant_name, external_id))
    cursor.execute("""
    INSERT INTO merchant_offers (entity_id, merchant_name, external_id, affiliate_url, current_price, currency, in_stock, rating, review_count, last_checked_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (entity_id, merchant_name, external_id, affiliate_url, current_price, currency, in_stock, rating, review_count))
    mid = cursor.lastrowid
    conn.commit()
    conn.close()
    return mid

def get_merchant_offers(entity_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM merchant_offers WHERE entity_id = ? ORDER BY current_price ASC", (entity_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

# Khởi tạo DB ngay khi load
init_db()

