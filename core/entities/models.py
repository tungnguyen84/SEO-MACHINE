"""
Data Models for Products, Vehicles, Specs, and Attributes
"""
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class EntityType(str, Enum):
    POWER_STATION = "power_station"
    PORTABLE_FRIDGE = "portable_fridge"
    SOLAR_PANEL = "solar_panel"
    VEHICLE = "vehicle"
    CAMPING_GEAR = "camping_gear"
    BATTERY_ACCESSORY = "battery_accessory"
    OTHER = "other"

class EntityAttribute(BaseModel):
    attr_key: str
    attr_value_num: Optional[float] = None
    attr_value_text: Optional[str] = None
    unit: Optional[str] = None
    confidence_score: float = 1.0
    verified_by_source_id: Optional[int] = None

class MerchantOfferModel(BaseModel):
    merchant_name: str
    external_id: str
    affiliate_url: str
    current_price: Optional[float] = None
    currency: str = "USD"
    in_stock: bool = True
    rating: Optional[float] = None
    review_count: Optional[int] = None

class Entity(BaseModel):
    id: str
    entity_type: EntityType
    brand: str
    model: str
    sku_or_upc: Optional[str] = None
    primary_image_url: Optional[str] = None
    attributes: Dict[str, EntityAttribute] = Field(default_factory=dict)
    merchant_offers: List[MerchantOfferModel] = Field(default_factory=list)
