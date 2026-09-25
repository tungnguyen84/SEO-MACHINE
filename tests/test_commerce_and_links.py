"""
Tests for Offer Failover (Priority 10) and Internal Link Rebalancing (Priority 9)
"""
import pytest
from core.database import init_db, get_connection
from core.entities.entity_manager import EntityManager
from core.commerce.offer_router import OfferRouter
from core.links.internal_link_worker import InternalLinkWorker

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_offer_failover():
    """
    Test that when the primary merchant offer (e.g. Amazon) is OUT_OF_STOCK,
    the router automatically fails over to the next eligible offer (e.g. Direct brand).
    Verifies that the canonical product specifications remain untouched.
    """
    entity_id = "test_fridge_failover"
    EntityManager.create_or_update_entity(
        entity_id=entity_id,
        entity_type="portable_fridge",
        brand="ICECO",
        model="VL45 Pro"
    )

    # 1. Add Amazon Offer (Primary Retailer)
    amazon_id = EntityManager.link_merchant(
        entity_id=entity_id,
        merchant_name="Amazon",
        external_id="B08XYZ123",
        affiliate_url="https://amazon.com/dp/B08XYZ123?tag=aff-20",
        price=499.0,
        in_stock=True
    )

    # 2. Add Direct Brand Offer
    direct_id = EntityManager.link_merchant(
        entity_id=entity_id,
        merchant_name="Direct",
        external_id="ICECO-VL45",
        affiliate_url="https://icecofreezer.com/vl45?ref=partner",
        price=529.0,
        in_stock=True
    )

    # Initial Selection: Direct or active in-stock offer
    best_initial = OfferRouter.select_best_offer(entity_id)
    assert best_initial is not None
    assert best_initial["in_stock"] == 1

    # Mark Amazon Offer as OUT_OF_STOCK
    OfferRouter.set_offer_status(amazon_id, status="OUT_OF_STOCK", in_stock=False)

    # Failover Selection: Must pick Direct offer!
    best_after = OfferRouter.select_best_offer(entity_id)
    assert best_after is not None
    assert best_after["merchant_name"] == "Direct"
    assert best_after["in_stock"] == 1

    # Canonical Product Entity attributes must remain intact!
    ent = EntityManager.get_entity(entity_id)
    assert ent["brand"] == "ICECO"
    assert ent["model"] == "VL45 Pro"

def test_internal_link_rebalance():
    """
    Test that InternalLinkWorker connects related articles and applies
    natural anchor text variations without exact-match spam.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Create entities and relationship
    EntityManager.create_or_update_entity("car_subaru", "vehicle", "Subaru", "Outback 2025")
    EntityManager.create_or_update_entity("fridge_iceco", "portable_fridge", "ICECO", "VL45")

    cursor.execute("""
    INSERT OR REPLACE INTO entity_relationships (subject_id, predicate, object_id, confidence)
    VALUES ('fridge_iceco', 'fits_in', 'car_subaru', 1.0)
    """)

    # Create articles
    cursor.execute("""
    INSERT INTO articles (workspace_id, title, slug, keyword, primary_entity_id, wp_link, status)
    VALUES (1, 'ICECO VL45 Review', 'iceco-vl45-review', 'iceco vl45 review', 'fridge_iceco', 'https://site.com/iceco-vl45', 'publish')
    """)
    art1_id = cursor.lastrowid

    cursor.execute("""
    INSERT INTO articles (workspace_id, title, slug, keyword, primary_entity_id, wp_link, status)
    VALUES (1, 'Subaru Outback Camping Setup', 'subaru-outback-camping', 'subaru outback camping', 'car_subaru', 'https://site.com/subaru-outback', 'publish')
    """)
    art2_id = cursor.lastrowid

    # Clean any prior test links
    cursor.execute("DELETE FROM internal_links WHERE source_url LIKE '%site.com%'")

    conn.commit()
    conn.close()

    # Run Rebalance Worker
    result = InternalLinkWorker.rebalance_internal_links(workspace_id=1)
    assert result["status"] == "COMPLETED"
    assert result["links_created"] >= 1

    # Verify internal link record
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM internal_links WHERE target_url = 'https://site.com/subaru-outback'")
    link_row = cursor.fetchone()
    conn.close()

    assert link_row is not None
    assert link_row["anchor_type"] in ["brand_model", "partial_match", "natural"]
    assert "Subaru" in link_row["anchor_text"]
