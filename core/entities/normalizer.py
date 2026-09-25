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
