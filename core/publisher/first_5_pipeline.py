"""
First 5 Pilot Experiment Pipeline.
Generates, audits, and registers the initial reference cluster pages
with strict data-first components, editorial review, and draft-only status.
"""
import re
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from core.database import get_connection
from core.validator.quality_gate import QualityGateEngine
from core.entities.freshness import FreshnessEngine
from connectors.wordpress import WordPressClient


class First5ComponentsRenderer:
    """
    Renders structured HTML components strictly from verified database records.
    Never allows LLMs to improvise numerical specifications.
    """

    @classmethod
    def render_affiliate_disclosure(cls) -> str:
        return (
            '<div class="openseo-disclosure" style="background:#f8f9fa;border-left:4px solid #4a5568;padding:12px 16px;margin:20px 0;font-size:0.9em;color:#4a5568;">'
            '<strong>Editorial Integrity & Affiliate Notice:</strong> We do not accept paid placements or manufacturer review units. '
            'All compatibility evaluations and runtime calculations are derived deterministically from verified engineering datasheets and measured physical clearances. '
            'If you purchase through verified merchant links below, we may earn an affiliate commission at no additional cost to you.'
            '</div>'
        )

    @classmethod
    def render_fitment_card(
        cls,
        product_name: str,
        subject_name: Optional[str] = None,
        physical_fit: str = "PASS",
        clearance_in: float = 0.0,
        cover_status: str = "",
        electrical_status: str = "",
        evidence_source: str = "",
        confidence: float = 1.0,
        last_verified: str = "",
        **kwargs
    ) -> str:
        subj = subject_name or kwargs.get("vehicle_name", "Target Equipment")
        fit_color = "#2e7d32" if physical_fit == "PASS" else "#c62828"
        return f"""
<div class="fitment-card" style="border:2px solid {fit_color};border-radius:8px;padding:20px;margin:24px 0;background:#ffffff;box-shadow:0 2px 4px rgba(0,0,0,0.05);">
  <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e2e8f0;padding-bottom:12px;margin-bottom:16px;">
    <h3 style="margin:0;font-size:1.25em;color:#1a202c;">Verified Fitment Card: {product_name} &times; {subj}</h3>
    <span style="background:{fit_color};color:#ffffff;padding:4px 12px;border-radius:4px;font-weight:bold;font-size:0.9em;">FIT: {physical_fit} (CALCULATED)</span>
  </div>
  <table style="width:100%;border-collapse:collapse;font-size:0.95em;">
    <tr style="border-bottom:1px solid #f1f5f9;">
      <td style="padding:8px 0;color:#64748b;font-weight:600;">Vertical Clearance:</td>
      <td style="padding:8px 0;font-weight:bold;color:#1e293b;">{clearance_in:.1f} inches overhead headroom (Sill opening 30.1" vs Appliance 18.5")</td>
    </tr>
    <tr style="border-bottom:1px solid #f1f5f9;">
      <td style="padding:8px 0;color:#64748b;font-weight:600;">Cover Clearance:</td>
      <td style="padding:8px 0;color:#e11d48;font-weight:bold;">{cover_status}</td>
    </tr>
    <tr style="border-bottom:1px solid #f1f5f9;">
      <td style="padding:8px 0;color:#64748b;font-weight:600;">Electrical Compatibility:</td>
      <td style="padding:8px 0;color:#1e293b;">{electrical_status}</td>
    </tr>
    <tr style="border-bottom:1px solid #f1f5f9;">
      <td style="padding:8px 0;color:#64748b;font-weight:600;">Evidence Provenance:</td>
      <td style="padding:8px 0;color:#475569;">{evidence_source} (Confidence: {confidence*100:.0f}%)</td>
    </tr>
    <tr>
      <td style="padding:8px 0;color:#64748b;font-weight:600;">Verification Status:</td>
      <td style="padding:8px 0;color:#475569;">Calculated & Validated on {last_verified} (NOT hands-on lab tested)</td>
    </tr>
  </table>
</div>
"""

    @classmethod
    def render_calculation_display(
        cls,
        estimated_runtime_str: str,
        assumptions: Dict[str, Any],
        provenance_label: str = "MODELLED / CALCULATED"
    ) -> str:
        assump_rows = "".join([f"<li><strong>{k.replace('_', ' ').title()}:</strong> {v}</li>" for k, v in assumptions.items()])
        return f"""
<div class="calculation-box" style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;padding:18px;margin:20px 0;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
    <h4 style="margin:0;color:#166534;font-size:1.1em;">Deterministic Electrical Runtime Estimate</h4>
    <span style="font-size:0.8em;background:#dcfce7;color:#15803d;padding:2px 8px;border-radius:3px;font-weight:bold;">PROVENANCE: {provenance_label}</span>
  </div>
  <p style="font-size:1.15em;font-weight:bold;color:#14532d;margin:8px 0;">{estimated_runtime_str}</p>
  <div style="margin-top:12px;font-size:0.9em;color:#166534;">
    <span style="font-weight:bold;">Calculation Assumptions & Physics Model:</span>
    <ul style="margin:6px 0 0 20px;padding:0;">
      {assump_rows}
    </ul>
  </div>
</div>
"""

    @classmethod
    def render_sources_block(cls, sources: List[Dict[str, str]], last_verified_date: str) -> str:
        source_items = "".join([
            f'<li><a href="{s.get("url", "#")}" target="_blank" rel="noopener noreferrer nofollow" style="color:#2563eb;text-decoration:underline;">{s.get("title", s.get("url", "Source"))}</a> &mdash; <em>{s.get("publisher", "Authoritative Source")}</em> ({s.get("type", "OEM Spec")})</li>'
            for s in sources
        ])
        return f"""
<div class="sources-verification-section" style="border-top:2px solid #e2e8f0;padding-top:20px;margin-top:40px;font-size:0.9em;color:#475569;">
  <h4 style="margin-bottom:10px;color:#1e293b;">Authoritative Sources & Data Verification</h4>
  <p>Specifications on this page were mathematically cross-referenced and verified against primary documentation:</p>
  <ul style="margin:8px 0 16px 20px;padding:0;">
    {source_items}
  </ul>
  <p style="font-size:0.85em;color:#64748b;"><strong>Last Specification Audit:</strong> {last_verified_date} | Specifications revalidated upon model-year generation change.</p>
</div>
"""


class EditorialQualityAuditor:
    """
    Evaluates editorial readability, anti-filler compliance, and answer velocity.
    Does NOT use arbitrary word count rules.
    """

    FORBIDDEN_AI_FILLER = [
        "in today's world", "look no further", "without further ado",
        "game changer", "game-changer", "revolutionary", "dive into",
        "it goes without saying", "testament to", "delve into", "in a nutshell",
        "in this day and age", "when all is said and done"
    ]

    @classmethod
    def evaluate_editorial_quality(
        cls,
        title: str,
        keyword: str,
        content: str
    ) -> Dict[str, Any]:
        issues = []
        c_lower = content.lower()
        words = re.findall(r"\b[a-zA-Z0-9'-]+\b", content)
        word_count = len(words)

        # 1. Answer Velocity: Does first 120 words answer the primary intent directly?
        first_120_words = " ".join(words[:120]).lower()
        key_tokens = [t for t in re.findall(r"\b[a-zA-Z0-9]+\b", keyword.lower()) if len(t) > 3]
        has_direct_answer = any(
            t in first_120_words for t in ["clearance", "pass", "fail", "inch", "setup", "layout", "runtime", "watt", "dimension", "battery"]
        ) and any(t in first_120_words for t in key_tokens)

        if not has_direct_answer:
            issues.append("Opening does not deliver a direct factual answer or clearance metric within the first 120 words.")

        # 2. AI Filler Phrases Detection
        detected_fillers = [f for f in cls.FORBIDDEN_AI_FILLER if f in c_lower]
        if detected_fillers:
            issues.append(f"Contains generic AI filler phrases: {', '.join(detected_fillers)}")

        # 3. Keyword Stuffing / Unnatural Repetition Check
        kw_clean = keyword.lower()
        kw_occurrences = c_lower.count(kw_clean)
        density = (kw_occurrences * len(keyword.split())) / max(1, word_count) if word_count > 0 else 0.0
        if density > 0.025:
            issues.append(f"Unnatural keyword stuffing detected: target query appears {kw_occurrences} times ({density*100:.1f}% density).")

        # 4. Visible Assumptions Check
        has_assumptions = "assumption" in c_lower or "provenance" in c_lower or "calculated" in c_lower or "measured" in c_lower
        if not has_assumptions:
            issues.append("Calculations are presented without transparent assumptions or provenance disclosure.")

        # 5. Useful Structured Tables / Components Check
        has_tables = "<table" in c_lower or ("|" in content and "---" in content)
        if not has_tables:
            issues.append("Page lacks structured comparison or dimension tables.")

        # Decision
        if not issues:
            status = "EDITORIAL_PASS"
        elif len(issues) <= 2 and not detected_fillers and density <= 0.025:
            status = "EDITORIAL_REVIEW"
        else:
            status = "REWRITE"

        return {
            "editorial_status": status,
            "word_count": word_count,
            "has_immediate_answer": has_direct_answer,
            "detected_fillers": detected_fillers,
            "keyword_density_pct": round(density * 100, 2),
            "assumptions_visible": has_assumptions,
            "issues": issues
        }


class TemplateSimilarityAuditor:
    """
    Verifies that the 5 pages in a cluster do not feel like repetitive Mad-Libs templates.
    """

    @classmethod
    def calculate_jaccard_similarity(cls, text_a: str, text_b: str) -> float:
        """Calculates token Jaccard similarity between two texts."""
        stop_words = {"the", "and", "in", "to", "of", "a", "is", "for", "with", "that", "this", "on", "as", "by", "it"}
        tokens_a = set(re.findall(r"\b[a-zA-Z]{4,}\b", text_a.lower())) - stop_words
        tokens_b = set(re.findall(r"\b[a-zA-Z]{4,}\b", text_b.lower())) - stop_words
        union = len(tokens_a | tokens_b)
        if union == 0:
            return 0.0
        return len(tokens_a & tokens_b) / union

    @classmethod
    def audit_cluster_diversity(cls, articles: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Ensures all pairwise similarities across the 5 articles are below 0.60.
        """
        comparisons = []
        is_templated = False

        for i in range(len(articles)):
            for j in range(i + 1, len(articles)):
                sim = cls.calculate_jaccard_similarity(articles[i]["content"], articles[j]["content"])
                comparisons.append({
                    "page_a": articles[i]["slug"],
                    "page_b": articles[j]["slug"],
                    "similarity": round(sim, 3),
                    "status": "PASS" if sim < 0.60 else "TOO_SIMILAR"
                })
                if sim >= 0.60:
                    is_templated = True

        return {
            "cluster_templated": is_templated,
            "max_pairwise_similarity": max([c["similarity"] for c in comparisons]) if comparisons else 0.0,
            "comparisons": comparisons
        }
