"""
Page Planner
Generates structured content briefs bound strictly to verified database entities,
engineering calculations, and search intent.
"""
from typing import Dict, Any, List, Optional
import re
import json
from core.database import (
    list_entities, get_entity, get_entity_attributes,
    get_compatibility, get_evidence_claims, get_connection
)
from core.engine.calculation import CalculationEngine
from core.engine.compatibility import CompatibilityEngine

class PagePlanner:
    """Orchestrates search intent detection, entity selection, and verified data brief generation."""

    @classmethod
    def detect_intent(cls, keyword: str) -> str:
        kw = keyword.lower()
        if " vs " in kw or " versus " in kw or " compare " in kw:
            return "VS_COMPARISON"
        if "fit in" in kw or "compatibility" in kw or "compatible with" in kw or "for my " in kw or "for " in kw and any(v in kw for v in ["outback", "rav4", "bronco", "subaru", "toyota", "ford", "suv", "car"]):
            return "COMPATIBILITY_GUIDE"
        if "runtime" in kw or "how long" in kw or "can run" in kw:
            return "ENGINEERING_RUNTIME"
        if "best" in kw or "top" in kw or "review" in kw or "roundup" in kw:
            return "ROUNDUP_BEST_FOR"
        return "IN_DEPTH_SPECS"

    @classmethod
    def plan_content(cls, keyword: str, target_entity_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Creates a factual, closed-context brief for LLM writer.
        No hallucinations permitted.
        """
        intent = cls.detect_intent(keyword)
        entities_data = []

        if target_entity_ids:
            for eid in target_entity_ids:
                ent = get_entity(eid)
                if ent:
                    entities_data.append(ent)
        else:
            # Auto-match entities based on keyword tokens
            all_ents = list_entities(limit=50)
            kw_clean = keyword.lower()
            matched = []
            for e in all_ents:
                brand_match = e["brand"].lower() in kw_clean
                model_match = any(token in kw_clean for token in e["model"].lower().split())
                if brand_match or model_match:
                    matched.append(e["id"])

            if not matched:
                # Default to top relevant seeded entities
                matched = [e["id"] for e in all_ents[:3]]

            for eid in matched:
                ent = get_entity(eid)
                if ent:
                    entities_data.append(ent)

        # Assemble verified facts
        verified_specs_table = []
        calculations = []
        compatibility_cards = []

        for ent in entities_data:
            eid = ent["id"]
            attrs = get_entity_attributes(eid)
            clean_attrs = {k: v["text"] or str(v["num"]) for k, v in attrs.items()}
            verified_specs_table.append({
                "entity_id": eid,
                "name": f"{ent['brand']} {ent['model']}",
                "type": ent["entity_type"],
                "specs": clean_attrs,
                "offers": ent.get("merchant_offers", [])
            })

        # Run calculations based on combinations
        power_stations = [e for e in entities_data if e["entity_type"] == "power_station"]
        fridges = [e for e in entities_data if e["entity_type"] == "portable_fridge"]
        vehicles = [e for e in entities_data if e["entity_type"] == "vehicle"]

        # Cross calculate power + fridge
        for p in power_stations:
            for f in fridges:
                comp = CompatibilityEngine.evaluate(p["id"], f["id"])
                calculations.append({
                    "subject": f"{p['brand']} {p['model']}",
                    "target": f"{f['brand']} {f['model']}",
                    "type": "Runtime Autonomy",
                    "result": comp.get("fit_detail"),
                    "html": comp.get("data_box_html")
                })

        # Cross calculate vehicle + fridge or vehicle + power
        for v in vehicles:
            for g in (fridges + power_stations):
                comp = CompatibilityEngine.evaluate(v["id"], g["id"])
                compatibility_cards.append({
                    "vehicle": f"{v['brand']} {v['model']}",
                    "gear": f"{g['brand']} {g['model']}",
                    "status": comp.get("compatibility_status"),
                    "detail": comp.get("fit_detail"),
                    "html": comp.get("data_box_html")
                })

        brief = {
            "keyword": keyword,
            "intent": intent,
            "entities": verified_specs_table,
            "calculations": calculations,
            "compatibility_cards": compatibility_cards,
            "allowed_claims": [
                "Only cite numbers explicitly provided in verified_specs_table and calculations.",
                "Answer the search query directly in the very first 100 words.",
                "Compare based on measured physics, capacity Wh, and physical dimensions."
            ],
            "prohibited_claims": [
                "Do NOT use 'we tested', 'our hands-on test', 'in our laboratory', or 'we drove'.",
                "Do NOT invent battery capacities or dimensions not listed in the facts.",
                "Do NOT claim subjective opinions as laboratory facts."
            ]
        }
        return brief

    @classmethod
    def _extract_semantic_fingerprint(cls, keyword: str) -> set:
        """Extracts core semantic tokens ignoring stop words and word order."""
        stop_words = {"for", "in", "the", "a", "an", "best", "top", "my", "to", "and", "of", "with", "guide", "setup", "review", "reviews"}
        tokens = re.findall(r"\b[a-z0-9]+\b", keyword.lower())
        meaningful = {t for t in tokens if t not in stop_words}
        normalized = set()
        for t in meaningful:
            if t in ["refrigerator", "cooler"]:
                normalized.add("fridge")
            elif t in ["camping", "camper"]:
                normalized.add("camp")
            else:
                normalized.add(t)
        return normalized

    @classmethod
    def cluster_keywords(
        cls,
        keywords: List[str],
        existing_planned_keywords: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Groups keywords by intent and semantic similarity.
        Decides deliberate action for each keyword:
        - CREATE: Primary keyword for a new pillar/cluster page.
        - MERGE: Sub-intent/variant to be merged into primary page (H2/H3/FAQ), preventing cannibalization.
        - UPDATE_EXISTING: Matches a keyword already targeted by an existing published page.
        - SKIP: Exact duplicate or trivial word order variation.
        - NOINDEX: Low quality, thin, or out-of-scope query.
        """
        existing_fingerprints = {}
        if existing_planned_keywords:
            for ekw in existing_planned_keywords:
                fp = frozenset(cls._extract_semantic_fingerprint(ekw))
                existing_fingerprints[fp] = ekw

        clusters = {}
        results = []

        for kw in keywords:
            kw_clean = kw.strip()
            fp = frozenset(cls._extract_semantic_fingerprint(kw_clean))
            intent = cls.detect_intent(kw_clean)

            # Check if matches existing published page
            existing_match = None
            for efp, orig_title in existing_fingerprints.items():
                overlap = len(fp & efp)
                union = len(fp | efp)
                jaccard = overlap / union if union > 0 else 0
                has_f1 = any(t in fp for t in ["fridge"])
                has_f2 = any(t in efp for t in ["fridge"])
                if has_f1 != has_f2:
                    continue
                if jaccard >= 0.60 or fp == efp:
                    existing_match = orig_title
                    break

            if existing_match:
                results.append({
                    "keyword": kw_clean,
                    "action": "UPDATE_EXISTING",
                    "target_page": existing_match,
                    "intent": intent,
                    "reason": f"Matches existing page '{existing_match}'. Update existing page instead of creating a duplicate."
                })
                continue

            # Check if matches a cluster already seen in this batch
            matched_cluster_id = None
            for cid, cluster_info in clusters.items():
                cluster_fp = cluster_info["fingerprint"]
                overlap = len(fp & cluster_fp)
                union = len(fp | cluster_fp)
                jaccard = overlap / union if union > 0 else 0

                # Specific product token differentiation
                has_product_1 = any(t in fp for t in ["iceco", "vl45", "dometic", "ecoflow", "jackery", "anker"])
                has_product_2 = any(t in cluster_fp for t in ["iceco", "vl45", "dometic", "ecoflow", "jackery", "anker"])

                has_power_1 = any(t in fp for t in ["power", "battery", "wiring", "socket", "inverter"])
                has_power_2 = any(t in cluster_fp for t in ["power", "battery", "wiring", "socket", "inverter"])

                has_fridge_1 = any(t in fp for t in ["fridge"])
                has_fridge_2 = any(t in cluster_fp for t in ["fridge"])

                # If product specificity, power intent, or gear category differs, do NOT merge
                if has_product_1 != has_product_2 or has_power_1 != has_power_2 or has_fridge_1 != has_fridge_2:
                    continue

                # Match if fingerprints match or high jaccard
                if jaccard >= 0.60 or fp == cluster_fp:
                    matched_cluster_id = cid
                    break
                elif has_product_1 and has_product_2:
                    # Both have same specific product and vehicle
                    prod_overlap = len(fp & cluster_fp & {"iceco", "vl45", "dometic", "ecoflow", "jackery", "anker"})
                    veh_overlap = len(fp & cluster_fp & {"outback", "forester", "rav4", "crv", "bronco", "subaru", "toyota", "ford", "honda"})
                    if prod_overlap > 0 and veh_overlap > 0:
                        matched_cluster_id = cid
                        break
                elif not has_product_1 and not has_product_2 and not has_power_1:
                    # Both are generic vehicle + gear roundups
                    if ("outback" in fp and "outback" in cluster_fp and "fridge" in fp and "fridge" in cluster_fp):
                        matched_cluster_id = cid
                        break

            if matched_cluster_id is None:
                cid = f"cluster_{len(clusters) + 1}"
                is_pillar = any(c in fp for c in ["camp", "camping"]) and not any(g in fp for g in ["fridge", "battery", "solar", "cooler"])
                is_power = any(t in fp for t in ["power", "battery", "wiring", "socket"])
                
                if is_pillar:
                    hierarchy_type = "PILLAR_OVERVIEW"
                elif is_power:
                    hierarchy_type = "SECTION_WITHIN_PILLAR"
                elif any(t in fp for t in ["iceco", "vl45", "dometic"]):
                    hierarchy_type = "DEDICATED_FITMENT_GUIDE"
                else:
                    hierarchy_type = "CATEGORY_ROUNDUP"

                clusters[cid] = {
                    "fingerprint": fp,
                    "primary_keyword": kw_clean,
                    "intent": intent,
                    "hierarchy_type": hierarchy_type
                }
                results.append({
                    "keyword": kw_clean,
                    "action": "CREATE",
                    "cluster_id": cid,
                    "primary_keyword": kw_clean,
                    "intent": intent,
                    "hierarchy_type": hierarchy_type,
                    "reason": f"Primary pillar query for {hierarchy_type}."
                })
            else:
                primary_kw = clusters[matched_cluster_id]["primary_keyword"]
                htype = clusters[matched_cluster_id]["hierarchy_type"]
                if fp == clusters[matched_cluster_id]["fingerprint"]:
                    action = "SKIP"
                    reason = f"Exact semantic duplicate of '{primary_kw}'. Skip to avoid keyword cannibalization."
                else:
                    action = "MERGE"
                    reason = f"Secondary intent variant for {htype}. Merge into '{primary_kw}' as sub-section or FAQ."

                results.append({
                    "keyword": kw_clean,
                    "action": action,
                    "cluster_id": matched_cluster_id,
                    "primary_keyword": primary_kw,
                    "intent": intent,
                    "hierarchy_type": htype,
                    "reason": reason
                })

        return results

    @classmethod
    def evaluate_page_decision(
        cls,
        keyword: str,
        target_entity_ids: Optional[List[str]] = None,
        existing_planned_keywords: Optional[List[str]] = None,
        min_evidence_count: int = 1
    ) -> Dict[str, Any]:
        """
        Evaluates page action against evidence availability and cannibalization.
        Priority 5: If evidence is missing or insufficient, returns RESEARCH_REQUIRED.
        """
        # First check clustering / cannibalization against existing pages
        clusters = cls.cluster_keywords([keyword], existing_planned_keywords=existing_planned_keywords)
        base_decision = clusters[0] if clusters else {"action": "CREATE", "reason": "New pillar query"}

        if base_decision["action"] in ["UPDATE_EXISTING", "SKIP", "MERGE", "NOINDEX"]:
            return base_decision

        # For potential CREATE pages, strictly verify evidence availability
        if target_entity_ids:
            total_claims = 0
            for eid in target_entity_ids:
                claims = get_evidence_claims(eid)
                total_claims += len(claims)

            if total_claims < min_evidence_count:
                return {
                    "keyword": keyword,
                    "action": "RESEARCH_REQUIRED",
                    "reason": f"Required evidence count not met ({total_claims} < {min_evidence_count}). Ground-truth ingestion needed before drafting content.",
                    "intent": cls.detect_intent(keyword),
                    "missing_evidence_entities": target_entity_ids
                }

        return base_decision

    @classmethod
    def create_page_plan(
        cls,
        target_keyword: str,
        intent_type: str,
        target_entity_ids: Optional[List[str]] = None,
        factual_brief: Optional[Dict[str, Any]] = None,
        workspace_id: int = 1,
        project_id: Optional[str] = None,
        plan_action: str = "CREATE"
    ) -> int:
        """
        Persists a page plan to the database and returns plan_id.
        """
        conn = get_connection()
        cursor = conn.cursor()
        entities_str = json.dumps(target_entity_ids or [])
        brief_str = json.dumps(factual_brief or {})

        cursor.execute("""
        INSERT INTO page_plans (
            workspace_id, project_id, target_keyword, intent_type,
            plan_action, target_entity_ids, factual_brief_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (workspace_id, project_id, target_keyword, intent_type, plan_action, entities_str, brief_str))

        plan_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return plan_id
