import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request, Response, Depends, Header
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.config import settings
from core.database import (
    get_db_stats, save_rank_record, get_recent_articles, save_article_record,
    get_user_by_id, deduct_credit, create_user,
    list_campaign_plans, get_campaign_plan, get_used_keywords, update_scheduled_post_keyword,
    get_keyword_content_repository,
    get_workspaces_for_user, create_workspace, delete_workspace
)
from saas_core.auth import SaaSAuthManager
from saas_core.task_worker import BackgroundJobManager
from saas_core.site_manager import ConnectedSiteManager
from saas_affiliate.sentiment_miner import AmazonReviewSentimentMiner
from saas_affiliate.geo_router import AmazonGeoRouter
from saas_affiliate.price_guard import AmazonPriceComplianceGuard
from saas_affiliate.link_cloaker import LinkCloaker
from saas_affiliate.diamond_hunter import DiamondNicheHunter
from saas_affiliate.campaign_scheduler import CampaignScheduler
from saas_affiliate.short_video_creator import AIShortVideoCreator
from saas_affiliate.indexer import SearchEngineFastIndexer
from saas_affiliate.social_webhook import SocialWebhookDispatcher
from saas_core.billing import SaaSBillingManager

from connectors.wordpress import WordPressClient
from connectors.amazon import AmazonConnector
from research.product_advisor import ProductKeywordAdvisor
from research.longtail import LongtailKeywordFinder
from pipeline.orchestrator import AffiliatePipelineOrchestrator
from seomachine.writer import AffiliateContentWriter
from claude_seo.tech_auditor import TechnicalAuditor
from claude_seo.geo_auditor import GeoAuditor
from claude_seo.schema_generator import SchemaGenerator
from claude_seo.schema_studio import SchemaStudio
from claude_seo.sitemap_auditor import SitemapAuditor
from claude_seo.pagespeed import PageSpeedChecker
from openseo_core.serp_tracker import SerpRankTracker
from openseo_core.backlink_analyzer import BacklinkAnalyzer
from openseo_core.site_crawler import SiteCrawler

app = FastAPI(title="OpenSEO 3-in-1 Commercial SaaS Suite")

WEB_DIR = Path(__file__).parent / "web"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")

# ----------------- Auth Helper -----------------
def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        # Mặc định user Admin ID 1 nếu không truyền token (giữ tương thích liền mạch)
        user = get_user_by_id(1)
        if user:
            return user
        return {"id": 1, "email": "admin@openseo.local", "plan_tier": "agency", "credits_remaining": 500}
    
    token = authorization.split(" ", 1)[1]
    payload = SaaSAuthManager.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token không hợp lệ hoặc đã hết hạn")
    
    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="Người dùng không tồn tại")
    return user

# ----------------- Request Models -----------------
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""

class ConnectSiteRequest(BaseModel):
    site_name: str
    site_url: str
    username: str
    app_password: str
    workspace_id: Optional[int] = 1

class CreateWorkspaceRequest(BaseModel):
    name: str
    amazon_tag_us: Optional[str] = "yourtag-20"

class CreateCloakedLinkRequest(BaseModel):
    slug: str
    title: str
    destination_url: str

class MineReviewsRequest(BaseModel):
    asin: str
    title: Optional[str] = ""

class AsyncGenerateRequest(BaseModel):
    keyword: str
    asins: List[str]
    category: str = "Buying Guides"
    site_id: Optional[int] = None
    dry_run: bool = True
    publish_immediately: bool = False

class AnalyzeProductRequest(BaseModel):
    url_or_asin: str

class FindKeywordsRequest(BaseModel):
    seed: str
    limit: int = 25

class GenerateArticleRequest(BaseModel):
    keyword: str
    asins: List[str]
    category: str = "Buying Guides"
    site_id: Optional[int] = None
    dry_run: bool = True
    publish_immediately: bool = False

class SingleReviewRequest(BaseModel):
    asin_or_url: str
    category: str = "Product Reviews"
    site_id: Optional[int] = None
    dry_run: bool = True
    publish_immediately: bool = False

class ComparisonRequest(BaseModel):
    asin_a: str
    asin_b: str
    category: str = "Product Comparisons"
    site_id: Optional[int] = None
    dry_run: bool = True
    publish_immediately: bool = False

class InformationalRequest(BaseModel):
    topic: str
    article_type: str = "how_to"
    related_asin: Optional[str] = None
    category: str = "How-To Guides"
    site_id: Optional[int] = None
    dry_run: bool = True
    publish_immediately: bool = False

class RewriteArticleRequest(BaseModel):
    content_or_url: str

class AuditUrlRequest(BaseModel):
    url: str

class AuditGeoRequest(BaseModel):
    url: str

class AuditSitemapRequest(BaseModel):
    url: str

# ----------------- Data Authority Engine Models -----------------
class CreateEntityRequest(BaseModel):
    id: str
    entity_type: str
    brand: str
    model: str
    sku_or_upc: Optional[str] = None
    primary_image_url: Optional[str] = None

class AddAttributeRequest(BaseModel):
    attr_key: str
    raw_value: Any
    unit: Optional[str] = None
    evidence_quote: Optional[str] = None

class CalculateRuntimeRequest(BaseModel):
    battery_wh: float
    device_watts: float
    is_ac_load: bool = True
    inverter_efficiency: float = 0.85
    ambient_temp_f: Optional[float] = 77.0

class CheckCompatibilityRequest(BaseModel):
    subject_id: str
    target_id: str

class GenerateBriefRequest(BaseModel):
    keyword: str
    entity_ids: Optional[List[str]] = None

class QualityGateRequest(BaseModel):
    title: str
    content: str
    allowed_numbers: Optional[List[float]] = None


class PageSpeedRequest(BaseModel):
    url: str
    strategy: str = "mobile"

class CheckSerpRequest(BaseModel):
    keyword: str
    domain: Optional[str] = ""

class BacklinkRequest(BaseModel):
    domain: str

class CrawlSiteRequest(BaseModel):
    url: str
    max_pages: int = 15

class CustomSchemaRequest(BaseModel):
    schema_type: str
    data: Dict[str, Any]

class UpdateConfigRequest(BaseModel):
    WP_URL: Optional[str] = None
    WP_USERNAME: Optional[str] = None
    WP_APP_PASSWORD: Optional[str] = None
    AMAZON_TAG: Optional[str] = None
    LLM_PROVIDER: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    SERPAPI_API_KEY: Optional[str] = None
    VALUESERP_API_KEY: Optional[str] = None
    GOOGLE_SEARCH_API_KEY: Optional[str] = None
    GOOGLE_SEARCH_CX: Optional[str] = None

class HuntDiamondsRequest(BaseModel):
    category_input: str
    site_id: Optional[int] = None
    save_plan: bool = True
    plan_days: int = 30

class UpdatePlanDayRequest(BaseModel):
    plan_id: Optional[int] = None
    day_number: int
    keyword: str
    title: str
    article_type: str = "roundup"
    asins: List[str] = []

class LaunchAutopilotRequest(BaseModel):
    dry_run: bool = False
    site_id: Optional[int] = None
    max_days: int = 30

class InspectSerpCompetitionRequest(BaseModel):
    keyword: str

class RecheckSerpRequest(BaseModel):
    keyword: str

class GenerateShortVideoRequest(BaseModel):
    title: str
    keyword: str
    products: Optional[List[Dict[str, Any]]] = None
    language: str = "en"
    voice: Optional[str] = None
    blog_url: Optional[str] = ""

class FastIndexRequest(BaseModel):
    url: str

class TestWebhookRequest(BaseModel):
    webhook_url: str

class SendArticleWebhookRequest(BaseModel):
    webhook_url: str
    article_data: Dict[str, Any]

class UpgradePlanRequest(BaseModel):
    plan_tier: str

# ----------------- Dashboard & Link Cloaker Redirect -----------------
VALID_SPA_TABS = {
    "overview", "analyzer", "keywords", "ranktracker", "backlinks", 
    "sitecrawler", "generator", "rewriter", "techaudit", "sitemap", 
    "pagespeed", "schemastudio", "geoseo", "sites", "sentiment", 
    "cloaker", "jobs", "campaign", "repository", "videocreator", "settings",
    "data-entities", "data-compatibility", "data-qualitygate",
    "audit", "staging"
}

@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route("/{tab_name}", methods=["GET", "HEAD"], response_class=HTMLResponse)
async def serve_dashboard(tab_name: str = ""):
    if tab_name and tab_name not in VALID_SPA_TABS:
        raise HTTPException(status_code=404, detail="Page Not Found")
    index_file = WEB_DIR / "index.html"
    return index_file.read_text(encoding="utf-8")

@app.get("/go/{slug}")
async def redirect_cloaked_link(slug: str, request: Request):
    """Bắt link bọc /go/slug, đếm số lượt click, ghi analytics và chuyển hướng 307 an toàn."""
    client_ip = request.client.host if request.client else "unknown"
    referer = request.headers.get("referer", "")
    user_agent = request.headers.get("user-agent", "")
    destination = LinkCloaker.resolve_and_record_click(slug, client_ip=client_ip, referer=referer, user_agent=user_agent)
    if not destination:
        raise HTTPException(status_code=404, detail="Link affiliate không tồn tại hoặc đã hết hạn")
    return RedirectResponse(url=destination, status_code=307)

# ----------------- SaaS Auth Endpoints -----------------
@app.post("/api/auth/login")
async def login(req: LoginRequest):
    res = SaaSAuthManager.authenticate_user(req.email, req.password)
    if not res:
        raise HTTPException(status_code=400, detail="Sai email hoặc mật khẩu")
    return {"success": True, "user": res}

@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    existing = SaaSAuthManager.authenticate_user(req.email, req.password)
    try:
        user_info = create_user(req.email, req.password, req.full_name)
        token = SaaSAuthManager.create_token(user_info["id"], user_info["email"], "starter")
        user_info["token"] = token
        user_info["plan_tier"] = "starter"
        user_info["credits_remaining"] = 25
        return {"success": True, "user": user_info}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Email này đã tồn tại trong hệ thống")

@app.get("/api/auth/me")
async def get_my_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "full_name": current_user.get("full_name") or "User",
        "plan_tier": current_user["plan_tier"],
        "credits_remaining": current_user["credits_remaining"]
    }

# ----------------- Workspaces / Projects Endpoints -----------------
@app.get("/api/workspaces")
async def list_workspaces(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {"workspaces": get_workspaces_for_user(current_user["id"])}

@app.post("/api/workspaces")
async def create_new_workspace(req: CreateWorkspaceRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    return create_workspace(current_user["id"], req.name, req.amazon_tag_us or "yourtag-20")

@app.delete("/api/workspaces/{workspace_id}")
async def remove_workspace(workspace_id: int, current_user: Dict[str, Any] = Depends(get_current_user)):
    delete_workspace(workspace_id, current_user["id"])
    return {"success": True}

# ----------------- Multi-Site Endpoints -----------------
@app.get("/api/sites")
async def list_connected_sites(workspace_id: Optional[int] = None, current_user: Dict[str, Any] = Depends(get_current_user)):
    return {"sites": ConnectedSiteManager.list_sites(workspace_id=workspace_id)}

@app.post("/api/sites")
async def connect_new_site(req: ConnectSiteRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    ws_id = req.workspace_id or 1
    res = ConnectedSiteManager.add_site(ws_id, req.site_name, req.site_url, req.username, req.app_password)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res

@app.delete("/api/sites/{site_id}")
async def delete_connected_site(site_id: int, current_user: Dict[str, Any] = Depends(get_current_user)):
    ConnectedSiteManager.delete_site(site_id)
    return {"success": True}

# ----------------- Affiliate Moats Endpoints -----------------
@app.post("/api/mine-reviews")
async def mine_amazon_reviews(req: MineReviewsRequest):
    miner = AmazonReviewSentimentMiner()
    return miner.mine_sentiment_for_asin(req.asin, req.title or "")

@app.get("/api/cloaked-links")
async def list_cloaked_links(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {"links": LinkCloaker.list_links(1)}

@app.post("/api/cloaked-links")
async def create_new_cloaked_link(req: CreateCloakedLinkRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    return LinkCloaker.create_cloaked_link(1, req.slug, req.title, req.destination_url)

@app.get("/api/analytics/clicks")
async def get_click_analytics(current_user: Dict[str, Any] = Depends(get_current_user)):
    return LinkCloaker.get_analytics(workspace_id=1)

# ----------------- Background Jobs Endpoints -----------------
@app.get("/api/jobs")
async def list_background_jobs():
    return {"jobs": BackgroundJobManager.list_jobs(1)}

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    job = BackgroundJobManager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job không tồn tại")
    return job

@app.post("/api/jobs/async-generate")
async def trigger_async_generate_article(req: AsyncGenerateRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    # Kiểm tra credit
    if current_user["credits_remaining"] <= 0 and not req.dry_run:
        raise HTTPException(status_code=403, detail="Tài khoản của bạn đã hết Credits! Vui lòng nâng cấp gói.")

    job_id = BackgroundJobManager.create_job(1, "generate_roundup")

    # Hàm thực thi trong background worker
    def worker_task(jid: str):
        BackgroundJobManager.update_job_progress(jid, 20, "running")
        orchestrator = AffiliatePipelineOrchestrator()
        
        # Lấy thông tin site nếu có chọn site_id
        if req.site_id:
            site = ConnectedSiteManager.get_site(req.site_id)
            if site:
                orchestrator.wp = WordPressClient(url=site["site_url"], username=site["username"], password=site["app_password"])

        BackgroundJobManager.update_job_progress(jid, 50, "running")
        res = orchestrator.run_roundup_pipeline(
            keyword=req.keyword,
            product_asins_or_urls=req.asins,
            category_name=req.category,
            publish_immediately=req.publish_immediately,
            dry_run=req.dry_run
        )
        
        file_name = ""
        if req.dry_run and res.get("file_path"):
            file_name = Path(res["file_path"]).name

        # Trừ credit nếu không phải dry-run
        if not req.dry_run and res.get("success"):
            deduct_credit(current_user["id"], 1)

        return {
            "success": res.get("success", False),
            "file_name": file_name,
            "title": res.get("article", {}).get("title"),
            "wp_result": res.get("wp_result")
        }

    BackgroundJobManager.dispatch_job(job_id, worker_task)
    return {"success": True, "job_id": job_id, "message": "Tác vụ đã được đưa vào hàng đợi xử lý ngầm"}

# ----------------- Diamond Hunter & 30-Day Autopilot Calendar Endpoints -----------------
@app.post("/api/campaign/hunt-diamonds")
async def hunt_diamonds(req: HuntDiamondsRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    hunter = DiamondNicheHunter()
    used_kw = list(get_used_keywords(workspace_id=1))
    plan_days = req.plan_days if req.plan_days and req.plan_days > 0 else 30
    blueprint = hunter.generate_blueprint(
        category_input=req.category_input,
        plan_days=plan_days,
        exclude_keywords=used_kw
    )
    plan_id = None
    if req.save_plan:
        scheduler = CampaignScheduler()
        plan_id = scheduler.persist_plan(blueprint, site_id=req.site_id, workspace_id=1)
    blueprint["plan_id"] = plan_id
    blueprint["excluded_keywords_count"] = len(used_kw)
    return blueprint

@app.post("/api/campaign/update-day")
async def update_campaign_day(req: UpdatePlanDayRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    if req.plan_id:
        update_scheduled_post_keyword(
            plan_id=req.plan_id,
            day_number=req.day_number,
            keyword=req.keyword,
            title=req.title,
            article_type=req.article_type,
            asins=req.asins
        )
    return {"success": True, "message": f"Đã cập nhật từ khóa ngày {req.day_number}"}

@app.post("/api/serp/inspect-competition")
async def inspect_serp_competition(req: InspectSerpCompetitionRequest):
    from saas_core.live_serp import LiveSerpEngine
    engine = LiveSerpEngine()
    return engine.analyze(req.keyword)

# ----------------- Keyword & Content Hub Endpoints -----------------
@app.get("/api/repository/keywords")
async def get_repository_keywords(current_user: Dict[str, Any] = Depends(get_current_user)):
    return get_keyword_content_repository(workspace_id=1)

@app.post("/api/repository/recheck-serp")
async def recheck_serp(req: RecheckSerpRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    from saas_core.live_serp import LiveSerpEngine
    engine = LiveSerpEngine()
    return engine.analyze(req.keyword)

# ----------------- AI Short Video Creator Endpoints -----------------
@app.get("/api/video/voices")
async def get_video_voices():
    creator = AIShortVideoCreator()
    return {"voices": creator.get_available_voices()}

@app.post("/api/video/generate-short")
async def generate_short_video(req: GenerateShortVideoRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    creator = AIShortVideoCreator()
    try:
        res = await creator.create_video_short(
            title=req.title,
            keyword=req.keyword,
            products=req.products or [],
            language=req.language,
            voice=req.voice,
            blog_url=req.blog_url or ""
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi sản xuất video short: {str(e)}")

# ----------------- Fast Indexing Engine Endpoints -----------------
@app.post("/api/indexer/ping")
async def ping_fast_indexing(req: FastIndexRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Đẩy ping URL bài viết tới IndexNow (Bing/Yandex) và Googlebot sitemap ping."""
    return SearchEngineFastIndexer.ping_all(req.url)

# ----------------- Social Webhook Syndication Endpoints -----------------
@app.post("/api/social/webhook/test")
async def test_social_webhook(req: TestWebhookRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Bắn thử gói test ping tới Webhook Make.com / Zapier / n8n."""
    return SocialWebhookDispatcher.test_webhook(req.webhook_url)

@app.post("/api/social/webhook/publish")
async def publish_social_webhook(req: SendArticleWebhookRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Gửi bài viết vừa publish lên webhook để Make/Zapier tự động đăng lên mạng xã hội."""
    return SocialWebhookDispatcher.send_article_published(req.webhook_url, req.article_data)

# ----------------- SaaS Billing & Subscriptions Endpoints -----------------
@app.get("/api/billing/plan")
async def get_billing_plan(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Lấy thông tin gói cước hiện tại, số credits và danh sách các gói dịch vụ."""
    return SaaSBillingManager.get_user_subscription(current_user["id"])

@app.post("/api/billing/upgrade")
async def upgrade_billing_plan(req: UpgradePlanRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Nâng cấp gói SaaS cho user và nạp thêm Credits."""
    return SaaSBillingManager.upgrade_plan(current_user["id"], req.plan_tier)

@app.get("/api/campaign/plans")
async def get_plans(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {"plans": list_campaign_plans(1)}

@app.get("/api/campaign/plans/{plan_id}")
async def get_plan_detail(plan_id: int, current_user: Dict[str, Any] = Depends(get_current_user)):
    plan = get_campaign_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Kế hoạch không tồn tại")
    return plan

@app.post("/api/campaign/plans/{plan_id}/launch-autopilot")
async def launch_autopilot(plan_id: int, req: LaunchAutopilotRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    plan = get_campaign_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Kế hoạch không tồn tại")
    
    required_credits = min(len(plan.get("posts", [])), req.max_days)
    if not req.dry_run and current_user["credits_remaining"] < required_credits:
        raise HTTPException(
            status_code=403, 
            detail=f"Cần ít nhất {required_credits} credits để đăng tự động {req.max_days} ngày (Hiện có: {current_user['credits_remaining']})"
        )

    job_id = BackgroundJobManager.create_job(1, "campaign_autopilot_30d")
    
    def autopilot_worker(jid: str):
        scheduler = CampaignScheduler()
        posts = plan.get("posts", [])[:req.max_days]
        total = len(posts)
        processed = 0

        for idx, p in enumerate(posts):
            p["site_id"] = req.site_id or p.get("site_id")
            scheduler.execute_single_post(p, dry_run=req.dry_run)
            processed += 1
            progress_pct = int((processed / total) * 100)
            BackgroundJobManager.update_job_progress(jid, progress_pct, "running")
            if not req.dry_run:
                deduct_credit(current_user["id"], 1)

        return {
            "success": True,
            "processed_posts": processed,
            "category": plan.get("category_name"),
            "dry_run": req.dry_run
        }

    BackgroundJobManager.dispatch_job(job_id, autopilot_worker)
    return {
        "success": True,
        "job_id": job_id,
        "message": f"Chiến dịch Autopilot 30 ngày ({plan['category_name']}) đã bắt đầu chạy ngầm!"
    }

# ----------------- Core OpenSEO & SEOMachine Endpoints -----------------
@app.get("/api/status")
async def get_system_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    wp_client = WordPressClient()
    wp_status = wp_client.test_connection()
    db_stats = get_db_stats()
    return {
        "wp": wp_status,
        "wp_url": settings.WP_URL,
        "amazon_tag": settings.AMAZON_TAG,
        "llm_provider": settings.LLM_PROVIDER,
        "site_name": settings.SITE_NAME,
        "db": db_stats,
        "user": current_user
    }

@app.get("/api/recent-articles")
async def get_articles_history():
    return {"articles": get_recent_articles(limit=15)}

@app.post("/api/analyze-product")
async def analyze_product(req: AnalyzeProductRequest):
    advisor = ProductKeywordAdvisor()
    res = advisor.analyze_product_url(req.url_or_asin)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to analyze product"))
    prod = res["product"]
    opportunities = [
        {
            "keyword": o.keyword,
            "search_volume": o.search_volume,
            "competition": o.competition,
            "opportunity_score": o.opportunity_score,
            "article_type": o.article_type,
            "recommendation_note": o.recommendation_note
        }
        for o in res["opportunities"]
    ]
    return {
        "success": True,
        "product": {
            "title": prod.title,
            "price": prod.price,
            "asin": prod.asin,
            "image_url": prod.image_url,
            "affiliate_url": prod.affiliate_url
        },
        "category": res["category"],
        "recommended_keyword": res["recommended_keyword"],
        "recommendation_reason": res["recommendation_reason"],
        "opportunities": opportunities
    }

@app.post("/api/find-keywords")
async def find_keywords(req: FindKeywordsRequest):
    finder = LongtailKeywordFinder()
    results = finder.find_buyer_keywords(req.seed, max_results=req.limit)
    return {
        "success": True,
        "keywords": [
            {
                "keyword": k.keyword,
                "intent": k.intent,
                "source": k.source,
                "volume": getattr(k, "volume", 1500),
                "kd": getattr(k, "kd", 22),
                "opportunity_score": getattr(k, "opportunity_score", 90),
                "rd_status": getattr(k, "rd_status", "0-2 RD (Rất Dễ Vượt)")
            }
            for k in results
        ]
    }

@app.post("/api/check-serp")
async def check_serp(req: CheckSerpRequest):
    tracker = SerpRankTracker()
    domain_to_check = req.domain or settings.WP_URL
    res = tracker.check_serp_ranking(req.keyword, target_domain=domain_to_check)
    try:
        save_rank_record(req.keyword, domain_to_check, res.get("rank"), res.get("status_message", ""))
    except Exception as e:
        print(f"[DB] Lỗi: {e}")
    return res

@app.post("/api/analyze-backlinks")
async def analyze_backlinks(req: BacklinkRequest):
    analyzer = BacklinkAnalyzer()
    return analyzer.analyze_domain(req.domain)

@app.post("/api/crawl-site")
async def crawl_site(req: CrawlSiteRequest):
    crawler = SiteCrawler(max_pages=req.max_pages)
    return crawler.crawl_site(req.url)

@app.post("/api/generate-article")
async def generate_article(req: GenerateArticleRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    orchestrator = AffiliatePipelineOrchestrator()
    if req.site_id:
        site = ConnectedSiteManager.get_site(req.site_id)
        if site:
            orchestrator.wp = WordPressClient(url=site["site_url"], username=site["username"], password=site["app_password"])

    res = orchestrator.run_roundup_pipeline(
        keyword=req.keyword,
        product_asins_or_urls=req.asins,
        category_name=req.category,
        publish_immediately=req.publish_immediately,
        dry_run=req.dry_run
    )
    file_name = ""
    if req.dry_run and res.get("file_path"):
        file_name = Path(res["file_path"]).name

    if not req.dry_run and res.get("success"):
        deduct_credit(current_user["id"], 1)

    return {
        "success": res.get("success", False),
        "dry_run": req.dry_run,
        "file_name": file_name,
        "title": res.get("article", {}).get("title"),
        "wp_result": res.get("wp_result", {})
    }

@app.post("/api/generate-single-review")
async def generate_single_review(req: SingleReviewRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    amz = AmazonConnector()
    prod = amz.get_product_details(req.asin_or_url)
    if not prod:
        raise HTTPException(status_code=400, detail="Không lấy được dữ liệu sản phẩm Amazon")

    miner = AmazonReviewSentimentMiner()
    sentiments = miner.mine_sentiment_for_asin(prod.asin, prod.title)
    
    writer = AffiliateContentWriter()
    art = writer.generate_single_product_review(prod)
    
    file_name = f"{art['slug']}.html"
    out_file = OUTPUT_DIR / file_name
    out_file.write_text(art["content"], encoding="utf-8")

    save_article_record(
        title=art["title"],
        slug=art["slug"],
        keyword=art["focus_kw"],
        asins=[prod.asin],
        status="dry_run" if req.dry_run else "publish",
        file_path=str(out_file)
    )

    wp_res = {}
    if not req.dry_run:
        if req.site_id:
            site = ConnectedSiteManager.get_site(req.site_id)
            wp = WordPressClient(url=site["site_url"], username=site["username"], password=site["app_password"]) if site else WordPressClient()
        else:
            wp = WordPressClient()

        cat_id = wp.get_or_create_category(req.category)
        media_id = wp.upload_media_from_url(prod.image_url, alt_text=prod.title) if prod.image_url else None
        wp_res = wp.create_post(
            title=art["title"],
            content=art["content"],
            slug=art["slug"],
            status="publish" if req.publish_immediately else "draft",
            categories=[cat_id] if cat_id else None,
            featured_media_id=media_id
        )
        deduct_credit(current_user["id"], 1)

    return {"success": True, "dry_run": req.dry_run, "file_name": file_name, "title": art["title"], "wp_result": wp_res}

@app.post("/api/generate-comparison")
async def generate_comparison(req: ComparisonRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    amz = AmazonConnector()
    prod_a = amz.get_product_details(req.asin_a)
    prod_b = amz.get_product_details(req.asin_b)
    if not prod_a or not prod_b:
        raise HTTPException(status_code=400, detail="Cần lấy đủ thông tin cả 2 sản phẩm A và B")

    writer = AffiliateContentWriter()
    art = writer.generate_vs_comparison(prod_a, prod_b)

    file_name = f"{art['slug']}.html"
    out_file = OUTPUT_DIR / file_name
    out_file.write_text(art["content"], encoding="utf-8")

    save_article_record(
        title=art["title"],
        slug=art["slug"],
        keyword=art["focus_kw"],
        asins=[prod_a.asin, prod_b.asin],
        status="dry_run" if req.dry_run else "publish",
        file_path=str(out_file)
    )

    wp_res = {}
    if not req.dry_run:
        if req.site_id:
            site = ConnectedSiteManager.get_site(req.site_id)
            wp = WordPressClient(url=site["site_url"], username=site["username"], password=site["app_password"]) if site else WordPressClient()
        else:
            wp = WordPressClient()

        cat_id = wp.get_or_create_category(req.category)
        wp_res = wp.create_post(title=art["title"], content=art["content"], slug=art["slug"], status="publish" if req.publish_immediately else "draft", categories=[cat_id] if cat_id else None)
        deduct_credit(current_user["id"], 1)

    return {"success": True, "dry_run": req.dry_run, "file_name": file_name, "title": art["title"], "wp_result": wp_res}

@app.post("/api/generate-informational")
async def generate_informational(req: InformationalRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    writer = AffiliateContentWriter()
    related_prod = None
    if req.related_asin:
        amz = AmazonConnector()
        related_prod = amz.get_product_details(req.related_asin)

    art = writer.generate_informational_article(
        topic=req.topic,
        article_type=req.article_type,
        related_product=related_prod
    )

    file_name = f"{art['slug']}.html"
    out_file = OUTPUT_DIR / file_name
    out_file.write_text(art["content"], encoding="utf-8")

    save_article_record(
        title=art["title"],
        slug=art["slug"],
        keyword=art["focus_kw"],
        asins=[related_prod.asin] if related_prod else [],
        status="dry_run" if req.dry_run else "publish",
        file_path=str(out_file)
    )

    wp_res = {}
    if not req.dry_run:
        if req.site_id:
            site = ConnectedSiteManager.get_site(req.site_id)
            wp = WordPressClient(url=site["site_url"], username=site["username"], password=site["app_password"]) if site else WordPressClient()
        else:
            wp = WordPressClient()

        cat_id = wp.get_or_create_category(req.category)
        wp_res = wp.create_post(
            title=art["title"],
            content=art["content"],
            slug=art["slug"],
            status="publish" if req.publish_immediately else "draft",
            categories=[cat_id] if cat_id else None
        )
        deduct_credit(current_user["id"], 1)

    return {"success": True, "dry_run": req.dry_run, "file_name": file_name, "title": art["title"], "wp_result": wp_res}

@app.post("/api/rewrite-article")
async def rewrite_article(req: RewriteArticleRequest):
    writer = AffiliateContentWriter()
    return writer.optimize_and_rewrite_article(req.content_or_url)

@app.post("/api/audit-url")
async def audit_technical_url(req: AuditUrlRequest):
    auditor = TechnicalAuditor()
    return auditor.audit_url(req.url)

@app.post("/api/audit-geo")
async def audit_geo_readiness(req: AuditGeoRequest):
    geo = GeoAuditor()
    return geo.audit_ai_readiness(req.url)

@app.post("/api/audit-sitemap")
async def audit_sitemap(req: AuditSitemapRequest):
    auditor = SitemapAuditor()
    return auditor.audit_sitemap(req.url)

@app.post("/api/check-pagespeed")
async def check_pagespeed(req: PageSpeedRequest):
    checker = PageSpeedChecker()
    return checker.check_pagespeed(req.url, strategy=req.strategy)

@app.post("/api/generate-custom-schema")
async def generate_custom_schema(req: CustomSchemaRequest):
    st = req.schema_type.lower()
    d = req.data
    if st == "faq":
        json_str = SchemaStudio.generate_faq_schema(d.get("items", []))
    elif st == "product":
        json_str = SchemaStudio.generate_product_schema(
            name=d.get("name", ""),
            price=d.get("price", "99.99"),
            currency=d.get("currency", "USD"),
            rating=float(d.get("rating", 4.8)),
            reviews_count=int(d.get("reviews", 100)),
            image_url=d.get("image", ""),
            sku=d.get("sku", "SKU-001")
        )
    elif st == "howto":
        json_str = SchemaStudio.generate_howto_schema(name=d.get("name", ""), steps=d.get("steps", []))
    else:
        raise HTTPException(status_code=400, detail="Unsupported schema type")
    return {"success": True, "json_ld": json_str}

@app.get("/api/preview/{file_name}")
async def preview_article(file_name: str):
    file_path = OUTPUT_DIR / file_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Article file not found")
    return HTMLResponse(content=file_path.read_text(encoding="utf-8"))

def mask_secret(val: Optional[str]) -> str:
    if not val:
        return ""
    if len(val) <= 8:
        return "••••••••"
    return val[:3] + "••••••••" + val[-3:]

@app.get("/api/config")
async def get_config():
    return {
        "WP_URL": settings.WP_URL,
        "WP_USERNAME": settings.WP_USERNAME,
        "WP_APP_PASSWORD": mask_secret(settings.WP_APP_PASSWORD),
        "AMAZON_TAG": settings.AMAZON_TAG,
        "LLM_PROVIDER": settings.LLM_PROVIDER,
        "GEMINI_API_KEY": mask_secret(settings.GEMINI_API_KEY),
        "SERPAPI_API_KEY": mask_secret(os.getenv("SERPAPI_API_KEY", "")),
        "VALUESERP_API_KEY": mask_secret(os.getenv("VALUESERP_API_KEY", "")),
        "GOOGLE_SEARCH_API_KEY": mask_secret(os.getenv("GOOGLE_SEARCH_API_KEY", "")),
        "GOOGLE_SEARCH_CX": mask_secret(os.getenv("GOOGLE_SEARCH_CX", "")),
        "DATAFORSEO_LOGIN": mask_secret(settings.DATAFORSEO_LOGIN),
        "DATAFORSEO_PASSWORD": mask_secret(settings.DATAFORSEO_PASSWORD)
    }

@app.post("/api/config")
async def update_config(req: UpdateConfigRequest):
    env_file = Path(__file__).parent / ".env"
    lines = []
    if env_file.exists():
        lines = env_file.read_text(encoding="utf-8").splitlines()
    updates = {k: v for k, v in req.dict().items() if v is not None and "••••" not in str(v)}
    new_lines = []
    seen_keys = set()
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            k = line.split("=", 1)[0].strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}")
                seen_keys.add(k)
                continue
        new_lines.append(line)
    for k, v in updates.items():
        if k not in seen_keys:
            new_lines.append(f"{k}={v}")
    env_file.write_text("\n".join(new_lines), encoding="utf-8")
    
    from dotenv import load_dotenv
    load_dotenv(env_file, override=True)
    settings.WP_URL = os.getenv("WP_URL", "")
    settings.WP_USERNAME = os.getenv("WP_USERNAME", "")
    settings.WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "")
    settings.AMAZON_TAG = os.getenv("AMAZON_TAG", "")
    settings.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
    settings.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    return {"success": True}

# ==============================================================================
# DATA AUTHORITY & FACTUAL ENGINE API ENDPOINTS
# ==============================================================================
from core.entities.entity_manager import EntityManager
from core.engine.calculation import CalculationEngine
from core.engine.compatibility import CompatibilityEngine
from core.planner.page_planner import PagePlanner
from core.validator.quality_gate import QualityGate
from core.niche_adapters.vehicle_camping import VehicleCampingAdapter

@app.get("/api/v1/entities")
async def api_list_entities(type: Optional[str] = None, q: Optional[str] = None):
    """Lấy danh sách các Thực Thể (sản phẩm, xe, phụ kiện) kèm số lượng verified specs."""
    ents = EntityManager.list_all(entity_type=type, search=q)
    return {"success": True, "count": len(ents), "entities": ents}

@app.get("/api/v1/entities/{entity_id}")
async def api_get_entity(entity_id: str):
    """Lấy thông tin chi tiết một Thực Thể kèm toàn bộ thông số, trích dẫn bằng chứng và liên kết thương mại."""
    ent = EntityManager.get_entity_full(entity_id)
    if not ent:
        raise HTTPException(status_code=404, detail="Entity not found")
    return {"success": True, "entity": ent}

@app.post("/api/v1/entities")
async def api_create_entity(req: CreateEntityRequest):
    """Tạo mới hoặc cập nhật một Thực Thể chuẩn."""
    ent = EntityManager.create_or_update_entity(
        entity_id=req.id,
        entity_type=req.entity_type,
        brand=req.brand,
        model=req.model,
        sku_or_upc=req.sku_or_upc,
        primary_image_url=req.primary_image_url
    )
    return {"success": True, "entity": ent}

@app.post("/api/v1/entities/{entity_id}/attributes")
async def api_add_entity_attribute(entity_id: str, req: AddAttributeRequest):
    """Thêm một thông số kỹ thuật chuẩn hóa kèm trích dẫn dẫn chứng."""
    attr_id = EntityManager.add_verified_attribute(
        entity_id=entity_id,
        attr_key=req.attr_key,
        raw_value=req.raw_value,
        unit=req.unit,
        evidence_quote=req.evidence_quote
    )
    return {"success": True, "attribute_id": attr_id}

@app.post("/api/v1/engine/calculate-runtime")
async def api_calculate_runtime(req: CalculateRuntimeRequest):
    """Tính toán thời gian chạy chính xác dựa trên công thức vật lý."""
    res = CalculationEngine.calculate_runtime(
        battery_wh=req.battery_wh,
        device_watts=req.device_watts,
        is_ac_load=req.is_ac_load,
        inverter_efficiency=req.inverter_efficiency
    )
    # Tính thêm tủ lạnh nếu tải ~45W
    fridge_res = CalculationEngine.calculate_fridge_runtime(
        battery_wh=req.battery_wh,
        fridge_rated_watts=req.device_watts,
        ambient_temp_f=req.ambient_temp_f or 77.0
    )
    return {"success": True, "runtime": res, "fridge_runtime": fridge_res}

@app.post("/api/v1/engine/check-compatibility")
async def api_check_compatibility(req: CheckCompatibilityRequest):
    """Đánh giá ma trận tương thích đa chiều giữa 2 thực thể (Xe + Thiết bị hoặc Trạm sạc + Tủ lạnh)."""
    res = CompatibilityEngine.evaluate(req.subject_id, req.target_id)
    return {"success": True, "evaluation": res}

@app.post("/api/v1/planner/generate-brief")
async def api_generate_brief(req: GenerateBriefRequest):
    """Lập dàn ý bài viết chuẩn xác, giới hạn trong các facts đã xác minh."""
    brief = PagePlanner.plan_content(keyword=req.keyword, target_entity_ids=req.entity_ids)
    return {"success": True, "brief": brief}

@app.post("/api/v1/validator/quality-gate")
async def api_quality_gate(req: QualityGateRequest):
    """Chấm điểm bài viết, phát hiện câu fake testing claims và kiểm tra tính xác thực số liệu."""
    allowed = set(req.allowed_numbers) if req.allowed_numbers else None
    res = QualityGate.audit_content(title=req.title, content=req.content, allowed_numbers=allowed)
    return {"success": True, "audit": res}

@app.post("/api/v1/niche/seed-defaults")
async def api_seed_niche_defaults():
    """Khởi tạo kho tri thức và các thực thể chuẩn cho ngách Xe dã ngoại & Cắm trại."""
    adapter = VehicleCampingAdapter()
    count = adapter.seed_default_entities()
    return {"success": True, "seeded_count": count, "message": f"Đã nạp thành công {count} thực thể và thông số chuẩn xác!"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Đang khởi động Full SaaS Suite tại: http://localhost:8000")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
