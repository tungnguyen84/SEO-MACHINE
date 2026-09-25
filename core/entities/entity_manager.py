"""
Entity Manager Service
Orchestrates entity creation, verified specifications normalization, and merchant links.
"""
from typing import Optional, List, Dict, Any
from core.database import (
    upsert_entity,
    get_entity,
    list_entities,
    upsert_entity_attribute,
    get_entity_attributes,
    add_source,
    add_evidence_claim,
    get_evidence_claims,
    upsert_merchant_offer,
    get_merchant_offers,
    upsert_compatibility,
    get_compatibility
)
from .normalizer import UnitNormalizer
from .models import EntityType

class EntityManager:
    """High-level management of domain entities, specs, and evidence."""

    @staticmethod
    def create_or_update_entity(
        entity_id: str,
        entity_type: str,
        brand: str,
        model: str,
        sku_or_upc: Optional[str] = None,
        primary_image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        return upsert_entity(
            entity_id=entity_id,
            entity_type=entity_type,
            brand=brand,
            model=model,
            sku_or_upc=sku_or_upc,
            primary_image_url=primary_image_url
        )

    @staticmethod
    def add_verified_attribute(
        entity_id: str,
        attr_key: str,
        raw_value: Any,
        unit: Optional[str] = None,
        confidence_score: float = 1.0,
        source_id: Optional[int] = None,
        evidence_quote: Optional[str] = None,
        page_number: Optional[int] = None
    ) -> int:
        """
        Normalizes raw value, inserts into entity_attributes, and optionally creates an evidence claim.
        """
        num_val, text_val, parsed_unit = UnitNormalizer.normalize_attribute(attr_key, raw_value)
        final_unit = unit or parsed_unit

        attr_id = upsert_entity_attribute(
            entity_id=entity_id,
            attr_key=attr_key,
            attr_value_num=num_val,
            attr_value_text=text_val,
            unit=final_unit,
            confidence_score=confidence_score,
            verified_by_source_id=source_id
        )

        if source_id and evidence_quote:
            add_evidence_claim(
                entity_id=entity_id,
                source_id=source_id,
                attribute_key=attr_key,
                extracted_value=text_val,
                raw_quote=evidence_quote,
                page_number=page_number,
                status="VERIFIED"
            )

        return attr_id

    @staticmethod
    def register_manual_source(
        entity_id: str,
        document_title: str,
        url: Optional[str] = None,
        archive_path: Optional[str] = None
    ) -> int:
        return add_source(
            entity_id=entity_id,
            source_type="user_manual_pdf",
            url=url,
            document_title=document_title,
            snapshot_archive_path=archive_path
        )

    @staticmethod
    def link_merchant(
        entity_id: str,
        merchant_name: str,
        external_id: str,
        affiliate_url: str,
        price: Optional[float] = None,
        in_stock: bool = True,
        rating: Optional[float] = None,
        review_count: Optional[int] = None
    ) -> int:
        return upsert_merchant_offer(
            entity_id=entity_id,
            merchant_name=merchant_name,
            external_id=external_id,
            affiliate_url=affiliate_url,
            current_price=price,
            currency="USD",
            in_stock=in_stock,
            rating=rating,
            review_count=review_count
        )

    @staticmethod
    def get_entity(entity_id: str) -> Optional[Dict[str, Any]]:
        return get_entity(entity_id)

    @classmethod
    def get_entity_full(cls, entity_id: str) -> Optional[Dict[str, Any]]:
        ent = get_entity(entity_id)
        if not ent:
            return None
        claims = get_evidence_claims(entity_id)
        ent["claims"] = claims
        ent["evidence_claims"] = claims
        ent["compatibility"] = get_compatibility(entity_id)

        # Calculate completeness score
        expected_keys = {
            EntityType.POWER_STATION.value: ["battery_capacity_wh", "inverter_continuous_watts", "inverter_surge_watts", "weight_lbs", "charge_time_ac_hours"],
            EntityType.PORTABLE_FRIDGE.value: ["volume_liters", "power_draw_watts", "dimensions_inches", "weight_lbs", "voltage_dc"],
            EntityType.VEHICLE.value: ["cargo_volume_cu_ft", "cargo_length_inches", "cargo_width_inches", "12v_outlet_location", "inverter_installed"]
        }

        req = expected_keys.get(ent.get("entity_type"), ["weight_lbs"])
        verified_count = sum(1 for a in ent.get("attributes", []) if a["attr_key"] in req)
        completeness = round((verified_count / len(req)) * 100, 1) if req else 100.0
        ent["spec_completeness_pct"] = completeness
        return ent

    @staticmethod
    def list_all(entity_type: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        return list_entities(entity_type=entity_type, search=search)
