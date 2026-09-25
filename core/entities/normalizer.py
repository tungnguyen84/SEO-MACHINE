"""
Unit Normalizer for Technical Specifications
Parses, cleans, and standardizes engineering and product units.
"""
import re
from typing import Tuple, Optional, Dict, Any

class UnitNormalizer:
    """Standardizes energy, electrical, physical dimension, and capacity measurements."""

    @staticmethod
    def parse_energy_wh(text: str) -> Optional[float]:
        """Parses Wh, kWh, mAh into standard Watt-hours (Wh)."""
        if not text:
            return None
        t = str(text).replace(",", "").strip()
        # e.g., 1002Wh, 1002 Wh, 1.002kWh, 50000mAh at 3.7V
        m_kwh = re.search(r"([\d\.]+)\s*kwh", t, re.IGNORECASE)
        if m_kwh:
            return float(m_kwh.group(1)) * 1000.0
        m_wh = re.search(r"([\d\.]+)\s*wh", t, re.IGNORECASE)
        if m_wh:
            return float(m_wh.group(1))
        m_mah = re.search(r"([\d\.]+)\s*mah", t, re.IGNORECASE)
        if m_mah:
            # Default to 3.7V nominal if voltage not specified
            return (float(m_mah.group(1)) * 3.7) / 1000.0
        # raw number if key implies wh
        m_num = re.search(r"^[\d\.]+$", t)
        if m_num:
            return float(m_num.group(0))
        return None

    @staticmethod
    def parse_power_watts(text: str) -> Optional[float]:
        """Parses Watts (W) or Kilowatts (kW)."""
        if not text:
            return None
        t = str(text).replace(",", "").strip()
        m_kw = re.search(r"([\d\.]+)\s*kw\b", t, re.IGNORECASE)
        if m_kw:
            return float(m_kw.group(1)) * 1000.0
        m_w = re.search(r"([\d\.]+)\s*w\b", t, re.IGNORECASE)
        if m_w:
            return float(m_w.group(1))
        m_num = re.search(r"^[\d\.]+$", t)
        if m_num:
            return float(m_num.group(0))
        return None

    @staticmethod
    def parse_weight_lbs(text: str) -> Optional[float]:
        """Parses pounds (lbs) or kilograms (kg) into standard lbs."""
        if not text:
            return None
        t = str(text).replace(",", "").strip()
        m_kg = re.search(r"([\d\.]+)\s*kg\b", t, re.IGNORECASE)
        if m_kg:
            return round(float(m_kg.group(1)) * 2.20462, 2)
        m_lbs = re.search(r"([\d\.]+)\s*(lbs|lb|pounds)\b", t, re.IGNORECASE)
        if m_lbs:
            return float(m_lbs.group(1))
        m_num = re.search(r"^[\d\.]+$", t)
        if m_num:
            return float(m_num.group(0))
        return None

    @staticmethod
    def parse_volume_liters(text: str) -> Optional[float]:
        """Parses volume into liters (L) from Quarts (qt) or Liters (L)."""
        if not text:
            return None
        t = str(text).replace(",", "").strip()
        m_qt = re.search(r"([\d\.]+)\s*(qt|quarts)\b", t, re.IGNORECASE)
        if m_qt:
            return round(float(m_qt.group(1)) * 0.946353, 1)
        m_l = re.search(r"([\d\.]+)\s*(l|liters|litre)\b", t, re.IGNORECASE)
        if m_l:
            return float(m_l.group(1))
        m_num = re.search(r"^[\d\.]+$", t)
        if m_num:
            return float(m_num.group(0))
        return None

    @staticmethod
    def parse_dimensions_inches(text: str) -> Optional[Dict[str, float]]:
        """
        Parses L x W x H in inches or cm/mm.
        Returns dict with length, width, height in inches.
        """
        if not text:
            return None
        t = str(text).lower().replace("inches", "in").replace('"', "in")
        is_cm = "cm" in t
        is_mm = "mm" in t
        # Match pattern: 25.2 x 15.7 x 15.6
        m = re.search(r"([\d\.]+)\s*(?:x|×|\*)\s*([\d\.]+)\s*(?:x|×|\*)\s*([\d\.]+)", t)
        if m:
            l, w, h = float(m.group(1)), float(m.group(2)), float(m.group(3))
            if is_cm:
                l, w, h = l / 2.54, w / 2.54, h / 2.54
            elif is_mm:
                l, w, h = l / 25.4, w / 25.4, h / 25.4
            return {
                "length_in": round(l, 2),
                "width_in": round(w, 2),
                "height_in": round(h, 2)
            }
        return None

    @classmethod
    def normalize_attribute(cls, attr_key: str, raw_val: Any) -> Tuple[Optional[float], str, str]:
        """
        Normalizes any technical key into (attr_value_num, attr_value_text, unit).
        """
        raw_str = str(raw_val).strip()
        key = attr_key.lower()

        if "capacity" in key or "wh" in key or "battery" in key:
            num = cls.parse_energy_wh(raw_str)
            return (num, f"{num}Wh" if num else raw_str, "Wh")

        if "power" in key or "watt" in key or "surge" in key or "output" in key:
            num = cls.parse_power_watts(raw_str)
            return (num, f"{num}W" if num else raw_str, "W")

        if "weight" in key or "lbs" in key or "kg" in key:
            num = cls.parse_weight_lbs(raw_str)
            return (num, f"{num} lbs" if num else raw_str, "lbs")

        if "volume" in key or "quart" in key or "liter" in key or "fridge_size" in key:
            num = cls.parse_volume_liters(raw_str)
            return (num, f"{num} L" if num else raw_str, "L")

        if isinstance(raw_val, (int, float)):
            num = float(raw_val)
            unit = "in" if any(d in key for d in ["height", "length", "width", "clearance", "inches"]) else ""
            return (num, f"{num} {unit}".strip(), unit)

        if any(d in key for d in ["height", "length", "width", "clearance", "inches"]):
            m = re.search(r"([\d\.]+)", raw_str)
            num = float(m.group(1)) if m else None
            return (num, f"{num} in" if num else raw_str, "in")

        return (None, raw_str, "")

    @classmethod
    def normalize_product_identity(
        cls,
        raw_name: str,
        brand: Optional[str] = None,
        sku: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extracts brand, base model, variant, and version.
        Ensures variants like 'ICECO VL45', 'ICECO VL45 Pro', 'ICECO VL45S' are
        strictly maintained as distinct entities and never falsely merged.
        """
        text = raw_name.strip()
        inferred_brand = brand
        if not inferred_brand:
            for b in ["ICECO", "Dometic", "EcoFlow", "Jackery", "Anker", "Bluetti", "BougeRV", "Setpower", "Alpicool"]:
                if b.lower() in text.lower():
                    inferred_brand = b
                    break
            if not inferred_brand:
                inferred_brand = text.split()[0] if text else "Generic"

        # Detect variants
        # e.g. Pro, ProS, S, Plus, Ultra, Max, Mini, Dual Zone
        variant = "Standard"
        if re.search(r"\bpro\s*s\b|\bpros\b", text, re.IGNORECASE):
            variant = "ProS"
        elif re.search(r"\bpro\b", text, re.IGNORECASE):
            variant = "Pro"
        elif re.search(r"\bvl45s\b|\b45s\b|\b[a-z0-9]+s\b", text, re.IGNORECASE) and not re.search(r"\bseries\b", text, re.IGNORECASE):
            variant = "S"
        elif re.search(r"\bplus\b|\b\+\b", text, re.IGNORECASE):
            variant = "Plus"
        elif re.search(r"\bmax\b", text, re.IGNORECASE):
            variant = "Max"
        elif re.search(r"\bdual\s*zone\b", text, re.IGNORECASE):
            variant = "DualZone"

        # Detect version / generation (e.g. V2, Gen 2, 2025)
        version = "v1"
        v_match = re.search(r"\b(v[0-9]|gen\s*[0-9]|202[0-9])\b", text, re.IGNORECASE)
        if v_match:
            version = v_match.group(1).lower().replace(" ", "")

        # Extract base model alphanumeric
        # Remove brand from name
        clean_name = re.sub(re.escape(inferred_brand), "", text, flags=re.IGNORECASE).strip()
        m_model = re.search(r"([a-zA-Z0-9\-]+)", clean_name)
        base_model = m_model.group(1) if m_model else clean_name

        slug_brand = inferred_brand.lower().replace(" ", "_")
        slug_model = base_model.lower().replace(" ", "_")
        slug_var = f"_{variant.lower()}" if variant != "Standard" else ""
        slug_ver = f"_{version.lower()}" if version != "v1" else ""
        
        canonical_id = f"prod_{slug_brand}_{slug_model}{slug_var}{slug_ver}"

        # If name is ambiguous or lacks clear model tokens
        uncertain = len(base_model) < 2 or (variant == "Standard" and ("?" in text or "series" in text.lower()))
        status = "REVIEW_REQUIRED" if uncertain else "CONFIRMED"

        return {
            "canonical_id": canonical_id,
            "brand": inferred_brand,
            "base_model": base_model,
            "variant": variant,
            "version": version,
            "sku": sku,
            "raw_name": raw_name,
            "identity_status": status
        }

    @classmethod
    def normalize_vehicle_identity(
        cls,
        raw_name: str,
        brand: Optional[str] = None,
        year: Optional[int] = None,
        trim: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scopes vehicle identity by Year, Generation, and Trim.
        Prevents assuming 2024 Outback == 2025 Outback or Base == Wilderness.
        """
        text = raw_name.strip()
        
        # Year
        inferred_year = year
        if not inferred_year:
            y_match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
            if y_match:
                inferred_year = int(y_match.group(1))

        # Brand
        inferred_brand = brand
        if not inferred_brand:
            for b in ["Subaru", "Toyota", "Ford", "Honda", "Jeep", "Chevrolet", "GMC", "Rivian", "Tesla"]:
                if b.lower() in text.lower():
                    inferred_brand = b
                    break
            if not inferred_brand:
                inferred_brand = text.split()[0] if text else "Vehicle"

        # Model
        clean = re.sub(re.escape(inferred_brand), "", text, flags=re.IGNORECASE)
        if inferred_year:
            clean = re.sub(str(inferred_year), "", clean)
        clean = clean.strip()

        # Trim
        inferred_trim = trim or "Base"
        known_trims = ["Wilderness", "Touring", "Limited", "Premium", "Onyx", "Sport", "TRD Off-Road", "Badlands", "Trailhawk", "Base"]
        for t in known_trims:
            if t.lower() in text.lower():
                inferred_trim = t
                break

        # Base Model
        model_words = [w for w in clean.split() if w.lower() not in [t.lower() for t in known_trims]]
        base_model = " ".join(model_words) if model_words else "Model"

        # Generation mapping for target vehicles
        generation = "Unknown"
        if inferred_brand.lower() == "subaru" and "outback" in base_model.lower():
            if inferred_year and 2020 <= inferred_year <= 2025:
                generation = "Gen 6 (BT)"
            elif inferred_year and 2015 <= inferred_year <= 2019:
                generation = "Gen 5 (BS)"

        slug_brand = inferred_brand.lower()
        slug_model = base_model.lower().replace(" ", "_")
        slug_year = f"_{inferred_year}" if inferred_year else "_unknown_year"
        slug_trim = f"_{inferred_trim.lower()}" if inferred_trim != "Base" else ""
        canonical_id = f"car_{slug_brand}_{slug_model}{slug_year}{slug_trim}"

        return {
            "canonical_id": canonical_id,
            "brand": inferred_brand,
            "model": base_model,
            "year": inferred_year,
            "generation": generation,
            "trim": inferred_trim,
            "is_year_scoped": inferred_year is not None,
            "is_trim_scoped": inferred_trim != "Base"
        }
