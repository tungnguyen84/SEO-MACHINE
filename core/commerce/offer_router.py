"""
Multi-Merchant Offer Router & Failover Engine
Priority 10 Implementation
Decouples canonical Product Entity from dynamic Merchant Offers.
Automatically selects next eligible merchant if primary offer is Out-of-Stock, Expired, or Invalid.
"""
from typing import Dict, Any, List, Optional
from core.database import get_merchant_offers, get_connection

class OfferRouter:
    """
    Renders the highest-converting active merchant offer,
    handling out-of-stock and expiration failovers automatically.
    """

    MERCHANT_PRIORITY = {
        "Direct": 1,
        "Amazon": 2,
        "eBay": 3
    }

    @classmethod
    def select_best_offer(cls, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Selects the best available offer for an entity.
        If primary offer is OUT_OF_STOCK or not ACTIVE, automatically fails over
        to the next active merchant without altering canonical product specifications.
        """
        all_offers = get_merchant_offers(entity_id)
        if not all_offers:
            return None

        # Filter active and in-stock offers
        eligible_offers = []
        for o in all_offers:
            is_active = o.get("offer_status", "ACTIVE") == "ACTIVE"
            in_stock = bool(o.get("in_stock", True))
            price_valid = o.get("current_price") is not None and o.get("current_price") > 0

            if is_active and in_stock and price_valid:
                eligible_offers.append(o)

        if not eligible_offers:
            # If no in-stock offer exists, return any active offer with OUT_OF_STOCK warning
            active_only = [o for o in all_offers if o.get("offer_status", "ACTIVE") == "ACTIVE"]
            return active_only[0] if active_only else all_offers[0]

        # Sort eligible offers by merchant priority and price
        def sort_key(offer):
            mname = offer.get("merchant_name", "Other")
            prio = cls.MERCHANT_PRIORITY.get(mname, 99)
            price = offer.get("current_price") or 999999.0
            return (prio, price)

        eligible_offers.sort(key=sort_key)
        return eligible_offers[0]

    @classmethod
    def set_offer_status(cls, offer_id: int, status: str, in_stock: bool) -> None:
        """Updates offer inventory and availability status."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE merchant_offers SET
            offer_status = ?,
            in_stock = ?,
            last_checked_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (status, 1 if in_stock else 0, offer_id))
        conn.commit()
        conn.close()
