"""
Page Planner
Generates structured content briefs bound strictly to verified database entities,
engineering calculations, and search intent across any active domain niche.
"""
from typing import Dict, Any, List, Optional, Set
import re
import json
from core.database import (
    list_entities, get_entity, get_entity_attributes,
    get_compatibility, get_evidence_claims, get_connection
)
from core.engine.calculation import CalculationEngine, CalculationRegistry
from core.engine.compatibility import CompatibilityEngine
from core.niche_adapters.base_adapter import NicheAdapter
from core.niche_adapters.registry import NicheRegistry


class PagePlanner:
    """Orchestrates search intent detection, entity selection, and verified data brief generation."""

    @classmethod
    def detect_intent(cls, keyword: str, adapter: Optional[NicheAdapter] = None) -> str:
        """Determines search intent using active adapter taxonomy or generic heuristics."""
        if adapter is None:
            adapter = NicheRegistry.get_active()

        kw = keyword.lower()
        if adapter and hasattr(adapter, "intent_taxonomy") and adapter.intent_taxonomy:
            for intent_name, tokens in adapter.intent_taxonomy.items():
                if any(t in kw for t in tokens):
                    return intent_name

        if " vs " in kw or " versus " in kw or " compare " in kw:
            return "VS_COMPARISON"
        if any(term in kw for term in ["fit in", "compatibility", "compatible with", "for my "]) or ("for " in kw and not any(r in kw for r in ["best", "top", "review"])):
            return "COMPATIBILITY_GUIDE"
        if "runtime" in kw or "how long" in kw or "can run" in kw:
            return "ENGINEERING_RUNTIME"
        if "best" in kw or "top" in kw or "review" in kw or "roundup" in kw:
            return "ROUNDUP_BEST_FOR"
        return "IN_DEPTH_SPECS"

    @classmethod
    def plan_content(
        cls,
        keyword: str,
        target_entity_ids: Optional[List[str]] = None,
        adapter: Optional[NicheAdapter] = None
    ) -> Dict[str, Any]:
        """
        Creates a factual, closed-context brief for LLM writer.
        No hallucinations permitted.
        """
        if adapter is None:
            adapter = NicheRegistry.get_active()

        intent = cls.detect_intent(keyword, adapter=adapter)
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

        # Dynamic cross-evaluation of entities across any registered domain
        for i, ent1 in enumerate(entities_data):
            for ent2 in entities_data[i+1:]:
                comp = CompatibilityEngine.evaluate(ent1["id"], ent2["id"])
                if comp.get("compatibility_status") != "UNKNOWN":
                    card = {
                        "subject": f"{ent1['brand']} {ent1['model']}",
                        "target": f"{ent2['brand']} {ent2['model']}",
                        "status": comp.get("compatibility_status"),
                        "detail": comp.get("fit_detail"),
                        "html": comp.get("data_box_html")
                    }
                    compatibility_cards.append(card)

                    if comp.get("runtime_calc"):
                        calculations.append({
                            "subject": f"{ent1['brand']} {ent1['model']}",
                            "target": f"{ent2['brand']} {ent2['model']}",
                            "type": "Runtime Autonomy",
                            "result": comp.get("fit_detail"),
                            "html": comp.get("data_box_html")
                        })

        allowed_claims = [
            "Only cite numbers explicitly provided in verified_specs_table and calculations.",
            "Answer the search query directly in the very first 100 words.",
            "Compare based on measured physics, capacity ratings, and physical dimensions."
        ]
        prohibited_claims = [
            "Do NOT use 'we tested', 'our hands-on test', 'in our laboratory', or 'we drove'.",
            "Do NOT invent capacities or dimensions not listed in the verified facts.",
            "Do NOT claim subjective opinions as laboratory facts."
        ]

        if adapter and hasattr(adapter, "quality_requirements"):
            extra_forbidden = adapter.quality_requirements.get("forbidden_claims", [])
            prohibited_claims.extend(extra_forbidden)

        brief = {
            "keyword": keyword,
            "intent": intent,
            "entities": verified_specs_table,
            "calculations": calculations,
            "compatibility_cards": compatibility_cards,
            "allowed_claims": allowed_claims,
            "prohibited_claims": prohibited_claims
        }
        return brief

    @classmethod
    def _extract_semantic_fingerprint(cls, keyword: str, adapter: Optional[NicheAdapter] = None) -> Set[str]:
        """Extracts core semantic tokens ignoring stop words and word order."""
        if adapter is None:
            adapter = NicheRegistry.get_active()

        stop_words = {"for", "in", "the", "a", "an", "best", "top", "my", "to", "and", "of", "with"}
        if adapter and hasattr(adapter, "get_domain_stop_words"):
            stop_words.update(adapter.get_domain_stop_words())

        tokens = re.findall(r"\b[a-z0-9]+\b", keyword.lower())
        meaningful = {t for t in tokens if t not in stop_words}

        if adapter and hasattr(adapter, "get_semantic_synonyms"):
            synonyms = adapter.get_semantic_synonyms()
            meaningful = {synonyms.get(t, t) for t in meaningful}

        return meaningful

    @classmethod
    def cluster_keywords(
        cls,
        keywords: List[str],
        existing_planned_keywords: Optional[List[str]] = None,
        adapter: Optional[NicheAdapter] = None
    ) -> List[Dict[str, Any]]:
        """
        Groups keywords by intent and semantic similarity across any niche.
        Prevents keyword cannibalization by assigning CREATE, MERGE, UPDATE_EXISTING, SKIP, or NOINDEX.
        """
        if adapter is None:
            adapter = NicheRegistry.get_active()

        existing_fingerprints = {}
        if existing_planned_keywords:
            for ekw in existing_planned_keywords:
                fp = frozenset(cls._extract_semantic_fingerprint(ekw, adapter=adapter))
                existing_fingerprints[fp] = ekw

        clusters = {}
        results = []

        differentiators = adapter.get_cluster_differentiators() if (adapter and hasattr(adapter, "get_cluster_differentiators")) else set()

        for kw in keywords:
            kw_clean = kw.strip()
            fp = frozenset(cls._extract_semantic_fingerprint(kw_clean, adapter=adapter))
            intent = cls.detect_intent(kw_clean, adapter=adapter)

            # Check if matches existing published page
            existing_match = None
            for efp, orig_title in existing_fingerprints.items():
                overlap = len(fp & efp)
                union = len(fp | efp)
                jaccard = overlap / union if union > 0 else 0

                if adapter and hasattr(adapter, "should_cluster"):
                    if adapter.should_cluster(set(fp), set(efp), jaccard):
                        existing_match = orig_title
                        break
                else:
                    if jaccard >= 0.50 or fp == efp:
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

                if adapter and hasattr(adapter, "should_cluster"):
                    if adapter.should_cluster(set(fp), set(cluster_fp), jaccard):
                        matched_cluster_id = cid
                        break
                else:
                    if jaccard >= 0.50 or fp == cluster_fp:
                        matched_cluster_id = cid
                        break

            if matched_cluster_id is None:
                cid = f"cluster_{len(clusters) + 1}"

                # Determine hierarchy type via adapter hook or clean generic logic
                if adapter and hasattr(adapter, "get_hierarchy_type"):
                    hierarchy_type = adapter.get_hierarchy_type(kw_clean, set(fp))
                else:
                    if len(fp) <= 2:
                        hierarchy_type = "PILLAR_OVERVIEW"
                    elif any(t in kw_clean.lower() for t in ["power", "battery", "wiring", "socket", "install", "maintenance"]):
                        hierarchy_type = "SECTION_WITHIN_PILLAR"
                    elif any(c in fp for c in ["fit", "compatible", "dimensions"]):
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
        min_evidence_count: int = 1,
        adapter: Optional[NicheAdapter] = None
    ) -> Dict[str, Any]:
        """
        Evaluates page action against evidence availability and cannibalization.
        If evidence is missing or insufficient, returns RESEARCH_REQUIRED.
        """
        clusters = cls.cluster_keywords([keyword], existing_planned_keywords=existing_planned_keywords, adapter=adapter)
        base_decision = clusters[0] if clusters else {"action": "CREATE", "reason": "New pillar query"}

        if base_decision["action"] in ["UPDATE_EXISTING", "SKIP", "MERGE", "NOINDEX"]:
            return base_decision

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
                    "intent": cls.detect_intent(keyword, adapter=adapter),
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
        """Persists a page plan to the database and returns plan_id."""
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
