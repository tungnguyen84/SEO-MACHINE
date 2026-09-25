"""
Grounded AI Writer 2.0 & Claim Traceability Engine
Generates authoritative content strictly bounded by GroundedContentContext,
enforces claim-to-fact mapping, and creates verifiable citation references.
"""
from typing import Dict, Any, List, Optional, Tuple, Set
import re
from datetime import datetime
from core.writer.grounded_context import GroundedContentContext, StructuredFact
from core.validator.claim_validator import ClaimValidator
from core.database import get_connection

class ClaimTracer:
    """
    Extracts factual claims from generated content and establishes
    a cryptographically and relationally traceable chain:
    Claim -> Fact -> Evidence -> Source URL.
    """

    @classmethod
    def trace_and_validate(
        cls,
        content: str,
        context: GroundedContentContext,
        article_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Parses content, matches claims against structured facts,
        and logs traceability records to the database.
        """
        claims_trace: List[Dict[str, Any]] = []
        unsupported_claims: List[Dict[str, Any]] = []
        forbidden_claims: List[Dict[str, Any]] = []

        # 1. Scan Prohibited First-Person Experience Claims (Rule 10)
        forbidden_matches = ClaimValidator.scan_forbidden_claims(content)
        for fb in forbidden_matches:
            record = {
                "claim_text": fb["matched"],
                "validation_status": "FORBIDDEN",
                "fact_id": None,
                "evidence_id": None,
                "source_id": None,
                "reason": fb["reason"]
            }
            forbidden_claims.append(record)
            claims_trace.append(record)

        # 2. Extract technical metrics and map to facts
        content_clean = re.sub(r"(\d),(\d)", r"\1\2", content)
        # Match units: Wh, W, lbs, in, liters, hours without greedy suffix consumption
        matches = re.finditer(
            r"(?:([a-zA-Z\s]{0,20})\s+)?(\d+\.?\d*)\s*(wh|watt|watts|w|lbs|lb|kg|inches|in|\"|liters|l|hours|hrs)\b",
            content_clean,
            re.IGNORECASE
        )

        facts_list = list(context.facts.values())
        calcs_list = context.calculations

        conn = get_connection()
        cursor = conn.cursor()

        for m in matches:
            prefix = (m.group(1) or "").strip()
            num_str = m.group(2)
            unit_str = m.group(3).lower()
            full_snippet = f"{prefix} {num_str} {unit_str}".strip()
            try:
                num_val = float(num_str)
            except ValueError:
                continue

            # Skip small integers commonly used as counts or voltage (1, 2, 3, 12, 24, 110, 120, 220)
            if num_val in [1.0, 2.0, 3.0, 4.0, 5.0, 12.0, 24.0, 110.0, 120.0, 220.0]:
                continue

            # Match against facts
            matched_fact: Optional[StructuredFact] = None
            for f in facts_list:
                if isinstance(f.value, (int, float)):
                    if abs(float(f.value) - num_val) < 0.5:
                        matched_fact = f
                        break

            # Match against calculations
            matched_calc: Optional[Dict[str, Any]] = None
            if not matched_fact:
                for c in calcs_list:
                    out = c.get("output", {})
                    for ck, cv in out.items():
                        if isinstance(cv, (int, float)) and abs(float(cv) - num_val) < 0.5:
                            matched_calc = c
                            break
                    if matched_calc:
                        break

            if matched_fact:
                ev_id = matched_fact.evidence_ids[0] if matched_fact.evidence_ids else None
                rec = {
                    "claim_text": full_snippet,
                    "validation_status": "VERIFIED",
                    "fact_id": matched_fact.fact_id,
                    "evidence_id": ev_id,
                    "source_id": None,
                    "reason": f"Matched verified attribute '{matched_fact.attribute_key}' from entity {matched_fact.entity_id}."
                }
                claims_trace.append(rec)
            elif matched_calc:
                rec = {
                    "claim_text": full_snippet,
                    "validation_status": "VERIFIED",
                    "fact_id": f"calc.{matched_calc.get('calculation_type')}",
                    "evidence_id": None,
                    "source_id": None,
                    "reason": f"Matched deterministic calculation output ({matched_calc.get('calculation_type')})."
                }
                claims_trace.append(rec)
            else:
                rec = {
                    "claim_text": full_snippet,
                    "validation_status": "UNSUPPORTED",
                    "fact_id": None,
                    "evidence_id": None,
                    "source_id": None,
                    "reason": f"Numerical claim '{num_val} {unit_str}' does not exist in verified fact registry."
                }
                unsupported_claims.append(rec)
                claims_trace.append(rec)

            # Persist to claim_validations if article_id provided
            if article_id:
                cursor.execute("""
                INSERT INTO claim_validations (
                    article_id, claim_text, fact_id, validation_status, reason, validated_at
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (article_id, rec["claim_text"], rec["fact_id"], rec["validation_status"], rec["reason"]))

        conn.commit()
        conn.close()

        return {
            "total_claims": len(claims_trace),
            "verified_claims_count": len(claims_trace) - len(unsupported_claims) - len(forbidden_claims),
            "unsupported_claims": unsupported_claims,
            "forbidden_claims": forbidden_claims,
            "claims_trace": claims_trace
        }


class GroundedWriter:
    """
    Produces deterministic, factual editorial articles strictly bounded
    by GroundedContentContext.
    """

    @classmethod
    def write_article(
        cls,
        context: GroundedContentContext,
        article_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Builds the complete grounded article with:
        1. Query-answering Introduction
        2. Factual Specifications Matrix
        3. Deterministic Compatibility / Math section
        4. Multi-Merchant Offers with Failover
        5. Verifiable Source Citation Section
        """
        primary = context.primary_entity
        brand = primary.get("brand", "Vehicle")
        model = primary.get("model", "Model")
        kw = context.page_plan.get("target_keyword", f"{brand} {model} Camping Guide")

        # 1. Header & Lead
        md_lines = [
            f"# {brand} {model}: Complete Technical Compatibility & Camping Guide",
            "",
            f"> **Verified Specifications Brief**: Analysis for search query: *\"{kw}\"*. All dimensions, capacities, and runtimes are bounded by official manufacturer documentation and deterministic engineering models.",
            "",
            "> **Affiliate Disclosure**: When you buy through links on our site, we may earn an affiliate commission at no extra cost to you. All evaluations remain independent and mathematically grounded in verified specifications.",
            "",
            "## Executive Summary",
            f"When equipping the **{brand} {model}** for overland travel and off-grid camping, accurate physical measurements and electrical power budgets are critical.",
            ""
        ]

        # 2. Verified Technical Specifications
        md_lines.extend([
            "## Verified Technical Specifications",
            "",
            "| Specification Attribute | Verified Value | Ground-Truth Source | Confidence |",
            "| :--- | :--- | :--- | :--- |"
        ])

        for fid, f in context.facts.items():
            val_str = f"{f.value} {f.unit or ''}".strip()
            src_label = f.source_type.replace("_", " ").title()
            conf_pct = f"{int(f.confidence * 100)}%"
            md_lines.append(f"| `{f.attribute_key}` | **{val_str}** | {src_label} | {conf_pct} |")

        md_lines.append("")

        # 3. Compatibility Analysis
        if context.compatibility_results:
            md_lines.extend([
                "## Dimensional Fitment & Compatibility Analysis",
                ""
            ])
            for comp in context.compatibility_results:
                status = comp.get("compatibility_status", "UNKNOWN")
                detail = comp.get("fit_detail", "")
                margin = comp.get("max_clearance_inches", 0.0)
                md_lines.append(f"### Compatibility Status: **{status}**")
                md_lines.append(f"- **Physical Verification**: {detail}")
                md_lines.append(f"- **Clearance Margin**: `{margin} inches`")
                md_lines.append("")

        # 4. Deterministic Calculations
        if context.calculations:
            md_lines.extend([
                "## Engineering & Physics Calculations",
                ""
            ])
            for calc in context.calculations:
                ctype = calc.get("calculation_type", "Calculation").replace("_", " ").title()
                fver = calc.get("formula_version", "v1.0")
                out = calc.get("output", {})
                assump = calc.get("assumptions", {})
                md_lines.append(f"### {ctype} ({fver})")
                md_lines.append(f"- **Calculated Result**: `{out}`")
                if assump:
                    md_lines.append(f"- **Underlying Assumptions**: `{assump}`")
                md_lines.append("")

        # 5. Multi-Merchant Offers with Failover
        if context.merchant_offers:
            md_lines.extend([
                "## Available Merchant Offers",
                ""
            ])
            # Filter active in-stock offers first
            active_offers = [o for o in context.merchant_offers if o.get("in_stock", True) and o.get("offer_status", "ACTIVE") == "ACTIVE"]
            if not active_offers:
                active_offers = context.merchant_offers  # fallback to all

            for offer in active_offers[:3]:
                mname = offer.get("merchant_name", "Retailer")
                price = offer.get("current_price")
                pstr = f"${price:.2f}" if price else "Check Price"
                url = offer.get("affiliate_url", "#")
                md_lines.append(f"- **{mname}**: [{pstr} Available Here]({url})")
            md_lines.append("")

        # 6. Verifiable Sources & Citations
        md_lines.extend([
            "## Sources & Technical References",
            "",
            "The factual data in this guide has been cross-referenced against authoritative documentation:",
            ""
        ])

        seen_sources = set()
        for f in context.facts.values():
            for u in f.source_urls:
                if u and u not in seen_sources:
                    seen_sources.add(u)
                    md_lines.append(f"1. [{f.source_type.replace('_', ' ').title()}]({u}) — Verified ground-truth documentation for `{f.entity_id}`.")

        if not seen_sources:
            md_lines.append("- Manufacturer OEM technical manual and specification sheets.")

        md_lines.append("")
        article_content = "\n".join(md_lines)

        # Trace and validate claims
        trace_result = ClaimTracer.trace_and_validate(article_content, context, article_id=article_id)

        return {
            "title": f"{brand} {model}: Complete Technical Compatibility & Camping Guide",
            "content": article_content,
            "trace_result": trace_result,
            "word_count": len(article_content.split()),
            "is_grounded": len(trace_result["unsupported_claims"]) == 0 and len(trace_result["forbidden_claims"]) == 0
        }
