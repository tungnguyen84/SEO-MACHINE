"""
Claim Inspector & User-Facing Fact Provenance Engine
Provides non-technical, human-understandable fact classifications and interactive claim audits:
- VERIFIED: Directly from official manufacturer datasheets or certification registries
- CALCULATED: Derived through validated mathematical formulas (e.g. annual electricity cost)
- MODELLED: Recommended through deterministic suitability and compatibility rules
- ASSUMPTION: Standard operational baselines (e.g., 12 hours/day runtime, $0.16/kWh utility tariff)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class UserFacingClaim(BaseModel):
    """User-facing claim record without exposing internal database or ORM details."""
    claim_id: str
    claim_text: str
    classification: str  # "Verified fact" | "Calculated" | "Modelled" | "Assumption"
    source_name: str
    source_url: Optional[str] = None
    retrieved_date: str
    confidence: float
    unit: Optional[str] = None
    calculation_details: Optional[Dict[str, Any]] = None
    editorial_status: str = "APPROVED"  # "APPROVED" | "FLAGGED" | "REJECTED"


class EditorialReviewItem(BaseModel):
    """Structured article representation for editorial preview and review."""
    article_id: str
    title: str
    slug: str
    page_type: str
    intent: str
    status: str  # "DRAFT" | "UNDER_REVIEW" | "APPROVED" | "REJECTED" | "REWRITE_REQUESTED"
    content_markdown: str
    claims: List[UserFacingClaim] = Field(default_factory=list)
    unsupported_count: int = 0
    forbidden_count: int = 0
    calculated_count: int = 0
    verified_count: int = 0
    user_feedback: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ClaimInspector:
    """Audits content claims and classifies provenance into clean, intuitive categories."""

    @classmethod
    def inspect_claim(
        cls,
        claim_text: str,
        fact_meta: Optional[Dict[str, Any]] = None,
        calc_meta: Optional[Dict[str, Any]] = None
    ) -> UserFacingClaim:
        """Inspects a single factual claim and returns a structured, user-friendly audit."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if calc_meta:
            return UserFacingClaim(
                claim_id=f"claim_calc_{abs(hash(claim_text)) % 100000}",
                claim_text=claim_text,
                classification="Calculated",
                source_name="OpenSEO Deterministic Formula Engine",
                source_url=None,
                retrieved_date=now_str,
                confidence=1.0,
                unit=calc_meta.get("output_unit"),
                calculation_details={
                    "formula": calc_meta.get("formula"),
                    "inputs": calc_meta.get("inputs", {})
                }
            )

        if fact_meta:
            source_type = str(fact_meta.get("source_type", "MANUFACTURER")).upper()
            if "CERTIFICATION" in source_type or "GOVERNMENT" in source_type:
                cls_type = "Verified fact"
                sname = fact_meta.get("source_name", "ENERGY STAR / DOE Registry")
            elif "MANUFACTURER" in source_type:
                cls_type = "Verified fact"
                sname = fact_meta.get("source_name", "Official Manufacturer Specification")
            elif "RETAIL" in source_type:
                cls_type = "Modelled"
                sname = fact_meta.get("source_name", "Verified Retail Catalog")
            else:
                cls_type = "Assumption"
                sname = fact_meta.get("source_name", "Standard Operational Assumption")

            return UserFacingClaim(
                claim_id=f"claim_fact_{abs(hash(claim_text)) % 100000}",
                claim_text=claim_text,
                classification=cls_type,
                source_name=sname,
                source_url=fact_meta.get("source_url", "https://www.energystar.gov/productfinder/product/certified-dehumidifiers"),
                retrieved_date=fact_meta.get("retrieved_at", now_str),
                confidence=float(fact_meta.get("confidence", 0.95)),
                unit=fact_meta.get("unit")
            )

        # Baseline assumption fallback
        return UserFacingClaim(
            claim_id=f"claim_assump_{abs(hash(claim_text)) % 100000}",
            claim_text=claim_text,
            classification="Assumption",
            source_name="Standard US Residential Baseline",
            source_url=None,
            retrieved_date=now_str,
            confidence=0.85,
            unit=None
        )

    @classmethod
    def build_editorial_preview(
        cls,
        article_id: str,
        title: str,
        slug: str,
        page_type: str,
        intent: str,
        content_markdown: str,
        claims: Optional[List[UserFacingClaim]] = None
    ) -> EditorialReviewItem:
        """Packages an article into a full editorial review preview."""
        item_claims = claims or []
        v_count = sum(1 for c in item_claims if c.classification == "Verified fact")
        c_count = sum(1 for c in item_claims if c.classification == "Calculated")

        return EditorialReviewItem(
            article_id=article_id,
            title=title,
            slug=slug,
            page_type=page_type,
            intent=intent,
            status="UNDER_REVIEW",
            content_markdown=content_markdown,
            claims=item_claims,
            verified_count=v_count,
            calculated_count=c_count
        )


class EditorialReviewStore:
    """In-memory & database store for editorial review actions (Approve, Edit, Reject, Rewrite)."""

    _items: Dict[str, EditorialReviewItem] = {}

    @classmethod
    def save_item(cls, item: EditorialReviewItem):
        cls._items[item.article_id] = item

    @classmethod
    def get_item(cls, article_id: str) -> Optional[EditorialReviewItem]:
        return cls._items.get(article_id)

    @classmethod
    def list_items(cls) -> List[EditorialReviewItem]:
        return list(cls._items.values())

    @classmethod
    def update_status(cls, article_id: str, new_status: str, feedback: Optional[str] = None) -> EditorialReviewItem:
        item = cls._items.get(article_id)
        if not item:
            raise KeyError(f"Article {article_id} not found")
        item.status = new_status
        if feedback:
            item.user_feedback = feedback
        item.updated_at = datetime.now(timezone.utc).isoformat()
        return item
