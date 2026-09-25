"""
Page Planner
Generates structured content briefs bound strictly to verified database entities,
engineering calculations, and search intent.
"""
from typing import Dict, Any, List, Optional
import re
from core.database import list_entities, get_entity, get_entity_attributes, get_compatibility
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
