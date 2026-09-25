"""
Cross-Niche Adapter & Multi-Site Isolation Test Suite
Verifies that OpenSEO functions as a true Multi-Site + Multi-Niche Data Authority SaaS
without hardcoded niche coupling in core modules.
"""
import pytest
from core.niche_adapters.registry import NicheRegistry
from core.niche_adapters.base_adapter import NicheAdapter, Capability, RiskProfile, PageType, IntentType
from core.niche_adapters.vehicle_camping import VehicleCampingAdapter
from core.niche_adapters.coffee_equipment import CoffeeEquipmentAdapter
from core.niche_adapters.workshop_tools import WorkshopToolsAdapter
from core.niche_adapters.config_adapter import ConfigDrivenNicheAdapter, NicheCreationWizard
from core.engine.calculation import CalculationRegistry, CalculationEngine
from core.engine.compatibility import CompatibilityEngine, CompatibilityStatus
from core.planner.page_planner import PagePlanner
from core.entities.entity_manager import EntityManager
from core.entities.normalizer import UnitNormalizer
from core.writer.grounded_writer import GroundedWriter
from core.writer.grounded_context import GroundedContentContext, StructuredFact
from core.validator.quality_gate import QualityGate
from core.site_profile import SiteProfile, SiteManager
from connectors.wordpress import WordPressClient


def test_vehicle_adapter_still_passes():
    """1. VehicleCampingAdapter is registered and provides required specifications."""
    adapter = NicheRegistry.get("vehicle_camping")
    assert adapter is not None
    assert adapter.niche_id == "vehicle_camping"
    assert Capability.COMPATIBILITY in adapter.capabilities
    assert Capability.CALCULATION in adapter.capabilities

    specs = adapter.get_required_specs("vehicle")
    assert "cargo_height_inches" in specs
    assert "12v_dc_outlet_amps" in specs


def test_coffee_adapter_creates_entities_and_normalizes():
    """2 & 3. Coffee Equipment adapter creates entities and normalizes specs."""
    coffee_adapter = NicheRegistry.get("coffee_equipment")
    assert coffee_adapter is not None
    assert "coffee_machine" in coffee_adapter.entity_types
    assert "grinder" in coffee_adapter.entity_types

    # Create coffee entities
    machine_id = "test_machine_gaggia_classic_pro"
    EntityManager.create_or_update_entity(machine_id, "coffee_machine", "Gaggia", "Classic Pro")
    EntityManager.add_verified_attribute(machine_id, "grouphead_diameter_mm", 58.0, unit="mm")
    EntityManager.add_verified_attribute(machine_id, "machine_pressure_bar", 15.0, unit="bar")

    basket_id = "test_basket_ims_precision_58"
    EntityManager.create_or_update_entity(basket_id, "filter_basket", "IMS", "Precision Competition 18g")
    EntityManager.add_verified_attribute(basket_id, "basket_diameter_mm", 58.0, unit="mm")
    EntityManager.add_verified_attribute(basket_id, "basket_capacity_grams", 18.0, unit="g")

    m = EntityManager.get_entity(machine_id)
    b = EntityManager.get_entity(basket_id)
    assert m["brand"] == "Gaggia"
    assert b["model"] == "Precision Competition 18g"

    # Test brand normalization
    norm = UnitNormalizer.normalize_product_name("Gaggia Classic Pro EVO 2024", brand="Gaggia")
    assert norm["brand"] == "Gaggia"
    assert "classic" in norm["base_model"].lower()


def test_coffee_calculation_registry():
    """4. Coffee calculation registry executes brew ratio formula."""
    calc_res = CalculationRegistry.execute("coffee_brew_ratio", dose_grams=18.0, ratio=2.0, brew_method="espresso")
    assert calc_res["dose_grams"] == 18.0
    assert calc_res["target_yield_grams"] == 36.0
    assert "25 - 32 seconds" in calc_res["target_extraction_time"]


def test_coffee_page_planner_and_clustering():
    """5. PagePlanner clusters coffee queries without vehicle assumptions."""
    coffee_adapter = NicheRegistry.get("coffee_equipment")
    keywords = [
        "best 58mm basket for Gaggia Classic",
        "Gaggia Classic 58mm basket",
        "58mm basket for Gaggia Classic espresso",
        "Gaggia Classic portafilter basket 58mm"
    ]
    clusters = PagePlanner.cluster_keywords(keywords, adapter=coffee_adapter)
    assert len(clusters) == 4

    creates = [c for c in clusters if c["action"] == "CREATE"]
    assert len(creates) == 1, f"Expected 1 CREATE for near-duplicate coffee queries, got {len(creates)}"


def test_coffee_filter_basket_compatibility():
    """5b. CompatibilityEngine evaluates 58mm basket fit against commercial grouphead."""
    machine_id = "test_machine_gaggia_classic_pro"
    basket_58_id = "test_basket_ims_precision_58"
    comp = CompatibilityEngine.evaluate(basket_58_id, machine_id)

    assert comp["verdict"] == "PASS"
    assert comp["compatibility_status"] == CompatibilityStatus.PASS.value
    assert "58.0mm" in comp["fit_detail"]


def test_workshop_compatibility_and_calculations():
    """6. Workshop Tools adapter evaluates battery platform interoperability."""
    tool_id = "test_tool_dewalt_dcd996"
    EntityManager.create_or_update_entity(tool_id, "power_tool", "DeWalt", "DCD996 20V MAX XR Hammer Drill")
    EntityManager.add_verified_attribute(tool_id, "voltage_v", 20.0, unit="V")
    EntityManager.add_verified_attribute(tool_id, "battery_system", "DeWalt 20V MAX")

    battery_good = "test_batt_dewalt_5ah"
    EntityManager.create_or_update_entity(battery_good, "battery_platform", "DeWalt", "DCB205 20V MAX 5.0Ah")
    EntityManager.add_verified_attribute(battery_good, "voltage_v", 20.0, unit="V")
    EntityManager.add_verified_attribute(battery_good, "battery_system", "DeWalt 20V MAX")

    battery_bad = "test_batt_milwaukee_m18"
    EntityManager.create_or_update_entity(battery_bad, "battery_platform", "Milwaukee", "M18 REDLITHIUM 5.0Ah")
    EntityManager.add_verified_attribute(battery_bad, "voltage_v", 18.0, unit="V")
    EntityManager.add_verified_attribute(battery_bad, "battery_system", "Milwaukee M18")

    # Native match
    res_pass = CompatibilityEngine.evaluate(battery_good, tool_id)
    assert res_pass["verdict"] == "PASS"
    assert "seamlessly" in res_pass["fit_detail"]

    # Cross-brand mismatch
    res_fail = CompatibilityEngine.evaluate(battery_bad, tool_id)
    assert res_fail["verdict"] == "FAIL"
    assert "Cross-brand platform mismatch" in res_fail["fit_detail"]

    # Workshop calculation
    calc = CalculationRegistry.execute("workshop_battery_cuts", voltage_v=20.0, amp_hours_ah=5.0, cut_energy_wh=3.5)
    assert calc["total_pack_energy_wh"] == 100.0
    assert calc["estimated_cuts_count"] == 28


def test_multi_site_isolation_no_leakage():
    """7, 8, 9, 10. Multi-site isolation prevents leakage of credentials, GSC, and affiliate tags."""
    SiteManager.clear()

    site_a = SiteProfile(
        site_id="site_coffee",
        domain="espressoauthority.com",
        brand_name="Espresso Authority",
        niche_adapter_id="coffee_equipment",
        affiliate_tags={"amazon": "coffeetag-20"},
        wordpress_connection={"site_url": "https://espressoauthority.com", "username": "coffee_admin", "app_password": "pw_coffee_secret"},
        search_console_property="sc-domain:espressoauthority.com"
    )

    site_b = SiteProfile(
        site_id="site_workshop",
        domain="protoolbenchmark.com",
        brand_name="Pro Tool Benchmark",
        niche_adapter_id="workshop_tools",
        affiliate_tags={"amazon": "tooltag-20"},
        wordpress_connection={"site_url": "https://protoolbenchmark.com", "username": "tool_admin", "app_password": "pw_tool_secret"},
        search_console_property="sc-domain:protoolbenchmark.com"
    )

    SiteManager.register_site(site_a)
    SiteManager.register_site(site_b)

    # 1. Affiliate tags isolation
    assert SiteManager.get_affiliate_tag("site_coffee") == "coffeetag-20"
    assert SiteManager.get_affiliate_tag("site_workshop") == "tooltag-20"
    assert SiteManager.get_affiliate_tag("site_coffee") != SiteManager.get_affiliate_tag("site_workshop")

    # 2. WordPress credentials isolation
    wp_a = WordPressClient.from_site_profile(site_a)
    wp_b = WordPressClient.from_site_profile(site_b)
    assert wp_a.username == "coffee_admin"
    assert wp_b.username == "tool_admin"
    assert wp_a.base_url != wp_b.base_url

    # 3. GSC property isolation
    assert SiteManager.get_gsc_property("site_coffee") == "sc-domain:espressoauthority.com"
    assert SiteManager.get_gsc_property("site_workshop") == "sc-domain:protoolbenchmark.com"
    assert SiteManager.get_gsc_property("site_coffee") != SiteManager.get_gsc_property("site_workshop")

    # 4. Audit Log isolation
    SiteManager.log_action("tenant_1", "site_coffee", "p_1", "editor", "PUBLISH", "article", "art_101")
    SiteManager.log_action("tenant_1", "site_workshop", "p_2", "admin", "UPDATE", "tool", "tool_202")

    logs_a = SiteManager.get_audit_logs("site_coffee")
    logs_b = SiteManager.get_audit_logs("site_workshop")
    assert len(logs_a) == 1
    assert len(logs_b) == 1
    assert logs_a[0].entity_id == "art_101"
    assert logs_b[0].entity_id == "tool_202"


def test_generic_writer_no_vehicle_assumptions():
    """11. GroundedWriter operates purely on domain facts without vehicle or camping terms."""
    # Set Coffee as active adapter
    NicheRegistry.set_active("coffee_equipment")

    coffee_machine = {
        "id": "test_gaggia_evo",
        "brand": "Gaggia",
        "model": "Classic EVO Pro",
        "entity_type": "coffee_machine"
    }

    facts = {
        "grouphead_diameter_mm": StructuredFact(
            fact_id="fact_1",
            entity_id="test_gaggia_evo",
            attribute_key="grouphead_diameter_mm",
            value=58.0,
            unit="mm",
            confidence=1.0,
            source_type="MANUFACTURER"
        ),
        "machine_pressure_bar": StructuredFact(
            fact_id="fact_2",
            entity_id="test_gaggia_evo",
            attribute_key="machine_pressure_bar",
            value=9.0,
            unit="bar",
            confidence=1.0,
            source_type="MANUFACTURER"
        )
    }

    ctx = GroundedContentContext(
        page_plan={
            "target_keyword": "Gaggia Classic EVO Pro Grouphead Size",
            "title": "Gaggia Classic EVO Pro: Complete Technical Specifications"
        },
        primary_entity=coffee_machine,
        facts=facts
    )

    art = GroundedWriter.generate_draft(ctx)
    content = art["content"]

    # Verify no vehicle terminology leaked
    for forbidden in ["vehicle", "car", "cargo", "hatch", "fridge", "subaru", "outback"]:
        assert forbidden not in content.lower(), f"Forbidden vehicle token '{forbidden}' leaked into coffee article!"

    # Verify coffee context generated accurately
    assert "Gaggia" in art["title"]
    assert "58.0 mm" in content
    assert art["is_grounded"] is True

    # Reset active adapter to vehicle_camping
    NicheRegistry.set_active("vehicle_camping")


def test_quality_gate_across_adapters():
    """12. QualityGate enforces integrity across any niche."""
    # Coffee draft
    coffee_content = """
    # Gaggia Classic EVO Specifications
    ## Executive Summary
    Analysis of technical extraction parameters.
    | Spec | Value |
    |---|---|
    | Grouphead | 58.0 mm |
    > **Affiliate Disclosure**: We earn commissions from qualifying purchases.
    """
    res = QualityGate.audit_content(
        title="Gaggia Classic EVO Specifications",
        content=coffee_content,
        allowed_numbers={58.0},
        has_primary_evidence=True,
        is_compatibility_valid=True
    )
    assert res["is_passed"] is True
    assert res["final_decision"] == "INDEX"
    assert res["quality_score"] >= 80.0


def test_config_driven_niche_creation_and_loading():
    """13. Declarative YAML config-driven adapter loads and operates."""
    config = NicheCreationWizard.create_niche_template(
        niche_id="3d_printers",
        name="Consumer 3D Printers & Filaments",
        capabilities=["PRODUCT_DATABASE", "TECHNICAL_SPECS", "COMPARISON"],
        entity_types=["printer", "filament"],
        risk_profile="LOW"
    )
    config["attributes"]["printer"] = [
        {"key": "nozzle_diameter_mm", "display_name": "Nozzle Size", "data_type": "numeric", "unit_type": "mm", "required": True},
        {"key": "max_bed_temp_c", "display_name": "Max Bed Temperature", "data_type": "numeric", "unit_type": "°C", "required": True}
    ]

    adapter = ConfigDrivenNicheAdapter(config)
    assert adapter.niche_id == "3d_printers"
    assert adapter.name == "Consumer 3D Printers & Filaments"
    assert Capability.PRODUCT_DATABASE in adapter.capabilities
    assert "printer" in adapter.entity_types

    req_specs = adapter.get_required_specs("printer")
    assert "nozzle_diameter_mm" in req_specs
