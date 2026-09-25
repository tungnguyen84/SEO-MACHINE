"""
Grounded Content Context & Structured Fact Registry
Provides immutable ground-truth specifications and calculations to the AI Writer.
"""
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import json
from core.database import (
    get_entity, get_entity_attributes, get_evidence_claims,
    get_compatibility, get_merchant_offers, get_connection
)

@dataclass
class StructuredFact:
    fact_id: str
    entity_id: str
    attribute_key: str
    value: Any
    unit: Optional[str] = None
    confidence: float = 1.0
    evidence_ids: List[int] = field(default_factory=list)
    source_type: str = "oem_manual"
    source_urls: List[str] = field(default_factory=list)
    verified_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "entity_id": self.entity_id,
            "attribute_key": self.attribute_key,
            "value": self.value,
            "unit": self.unit,
            "confidence": self.confidence,
            "evidence_ids": self.evidence_ids,
            "source_type": self.source_type,
            "source_urls": self.source_urls,
            "verified_at": self.verified_at
        }

@dataclass
class GroundedContentContext:
    page_plan: Dict[str, Any]
    primary_entity: Dict[str, Any]
    related_entities: List[Dict[str, Any]] = field(default_factory=list)
    facts: Dict[str, StructuredFact] = field(default_factory=dict)
    calculations: List[Dict[str, Any]] = field(default_factory=list)
    compatibility_results: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    merchant_offers: List[Dict[str, Any]] = field(default_factory=list)
    internal_link_candidates: List[Dict[str, Any]] = field(default_factory=list)
    allowed_claims: List[str] = field(default_factory=list)
    prohibited_claims: List[str] = field(default_factory=list)

    @classmethod
    def build(
        cls,
        page_plan: Dict[str, Any],
        primary_entity_id: str,
        related_entity_ids: Optional[List[str]] = None,
        calculations: Optional[List[Dict[str, Any]]] = None,
        internal_links: Optional[List[Dict[str, Any]]] = None
    ) -> "GroundedContentContext":
        """
        Assembles all verified evidence and entities into a closed, hallucination-proof context.
        """
        primary_entity = get_entity(primary_entity_id) or {"id": primary_entity_id, "brand": "Unknown", "model": "Unknown"}
        
        related_entities = []
        all_entity_ids = [primary_entity_id]
        if related_entity_ids:
            for rid in related_entity_ids:
                if rid != primary_entity_id:
                    rent = get_entity(rid)
                    if rent:
                        related_entities.append(rent)
                        all_entity_ids.append(rid)

        # Assemble Structured Fact Registry
        facts: Dict[str, StructuredFact] = {}
        all_evidence: List[Dict[str, Any]] = []

        conn = get_connection()
        cursor = conn.cursor()

        for eid in all_entity_ids:
            # 1. Attributes
            attrs = get_entity_attributes(eid)
            # 2. Evidence Claims with Source URLs
            cursor.execute("""
            SELECT ec.id, ec.attribute_key, ec.extracted_value, ec.raw_quote, ec.source_id, s.url, s.source_type
            FROM evidence_claims ec
            LEFT JOIN sources s ON ec.source_id = s.id
            WHERE ec.entity_id = ?
            """, (eid,))
            claim_rows = [dict(r) for r in cursor.fetchall()]
            all_evidence.extend(claim_rows)

            evidence_map = {}
            for cr in claim_rows:
                k = cr["attribute_key"]
                if k not in evidence_map:
                    evidence_map[k] = []
                evidence_map[k].append(cr)

            for k, a in attrs.items():
                val = a.get("num") if a.get("num") is not None else a.get("text")
                ev_list = evidence_map.get(k, [])
                ev_ids = [e["id"] for e in ev_list]
                src_urls = [e["url"] for e in ev_list if e.get("url")]
                src_type = ev_list[0]["source_type"] if ev_list else "manual"

                fid = f"{eid}.{k}"
                facts[fid] = StructuredFact(
                    fact_id=fid,
                    entity_id=eid,
                    attribute_key=k,
                    value=val,
                    unit=a.get("unit"),
                    confidence=float(a.get("confidence") or 1.0),
                    evidence_ids=ev_ids,
                    source_type=src_type,
                    source_urls=src_urls
                )

        conn.close()

        # Compatibility
        compatibility_results = []
        if len(all_entity_ids) >= 2:
            comp = get_compatibility(all_entity_ids[0], all_entity_ids[1])
            if comp:
                if isinstance(comp, list):
                    compatibility_results.extend(comp)
                else:
                    compatibility_results.append(comp)

        # Merchant Offers
        offers = []
        for eid in all_entity_ids:
            offers.extend(get_merchant_offers(eid))

        allowed_claims = [
            "Cite only verified dimensions, weights, capacities, and runtimes explicitly present in facts registry.",
            "If an attribute is marked UNKNOWN or absent, do not guess or approximate.",
            "Clearly distinguish calculated theoretical runtimes from static battery watt-hour ratings."
        ]

        prohibited_claims = [
            "Do NOT claim hands-on testing ('we tested', 'our tests', 'we bought', 'in our lab').",
            "Do NOT present speculative estimations as empirical measurements.",
            "Do NOT make authoritative claims without linking them to provided fact tokens."
        ]

        return cls(
            page_plan=page_plan,
            primary_entity=primary_entity,
            related_entities=related_entities,
            facts=facts,
            calculations=calculations or [],
            compatibility_results=compatibility_results,
            evidence=all_evidence,
            merchant_offers=offers,
            internal_link_candidates=internal_links or [],
            allowed_claims=allowed_claims,
            prohibited_claims=prohibited_claims
        )

    def get_allowed_numbers(self) -> Set[float]:
        """Returns the set of all authorized numeric values."""
        allowed = set()
        for f in self.facts.values():
            if isinstance(f.value, (int, float)):
                allowed.add(float(f.value))
        for c in self.calculations:
            out = c.get("output", {})
            for v in out.values():
                if isinstance(v, (int, float)):
                    allowed.add(float(v))
        return allowed
