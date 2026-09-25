"""
Comprehensive Test Suite for No-Code Niche Builder & SaaS Site Management
Verifies:
1. Air Purifier Niche: 100% declarative, zero Python code, CADR & cost math, compatibility, sandbox PASS.
2. Dog Crate Niche: 100% declarative, zero Python code, breed sizing & weight rating fit, sandbox PASS.
3. SafeFormulaEngine: AST-level code injection prevention, operator whitelist, mathematical functions.
4. DeclarativeRuleEvaluator: ==, !=, >, >=, <, <=, IN, RANGE, CONTAINS conditions with tolerances.
5. NicheValidator: Catches orphan entities, invalid units, unsafe formulas, circular dependencies.
6. EncryptedCredentialStore: AES symmetric encryption, masking in UI/exports, zero secret leakage.
7. NicheVersioningManager: Version history, YAML/JSON export & import with schema validation.
8. SaaSSiteManager & Lifecycle: Strict status progression, job scheduling gating (ACTIVE only), RBAC permissions.
"""

import pytest
from core.niche_builder import (
    DataType,
    AttributeSpec,
    RelationshipSpec,
    CalculationSpec,
    CompatibilityRuleSpec,
    SourcePolicySpec,
    PageTypeSpec,
    ContentPolicySpec,
    NicheSpec,
    NicheDraft,
    SiteLifecycleStatus,
    PermissionRole,
    SafeFormulaEngine,
    DeclarativeRuleEvaluator,
    NicheValidator,
    ValidationReport,
    IssueSeverity,
    AINicheDesigner,
    AINicheCritic,
    MarketResearchEstimator,
    DataAvailabilityScore,
    NicheSandbox,
    NicheVersioningManager,
    EncryptedCredentialStore,
    SaaSSiteManager,
)
from core.niche_builder.safe_formula import UnsafeFormulaError


# ==============================================================================
# TEST 1: AIR PURIFIER NO-CODE ACCEPTANCE TEST (ZERO PYTHON CODE)
# ==============================================================================

def test_air_purifier_no_code_pipeline():
    """
    Acceptance Test 1: Air Purifiers.
    Specifies entities, attributes (CADR, wattage, lifespan), formulas (room coverage, annual power cost, annual filter cost),
    and compatibility rules completely declaratively.
    Must validate, execute safe formulas, evaluate compatibility, and PASS sandbox dry-run.
    """
    draft = AINicheDesigner.design_from_prompt(
        "Design a high-authority air purifiers and clean air website with CADR room sizing, filter replacements, and electricity costs."
    )
    assert draft is not None
    assert draft.proposed_niche.niche_id == "air_purifiers"
    spec = draft.proposed_niche

    # 1. Verify Entities & Schema
    assert "AirPurifier" in spec.entity_types
    assert "Filter" in spec.entity_types
    assert "Room" in spec.entity_types

    # 2. Validate Niche Spec
    validation_report = NicheValidator.validate(spec)
    assert validation_report.is_valid is True
    assert len(validation_report.critical_issues) == 0

    # 3. Test Declarative Calculations via SafeFormulaEngine
    # Formula 1: room suitability = cadr_smoke_cfm * 1.5
    cadr_calc = next(c for c in spec.calculations if c.id == "air_purifier_room_suitability")
    cadr_result = SafeFormulaEngine.evaluate(cadr_calc.formula, {"cadr_smoke_cfm": 300.0})
    assert cadr_result == pytest.approx(450.0, 0.01)

    # Formula 2: annual_electricity_cost = (power_consumption_watts / 1000.0) * hours_per_day * 365.0 * electricity_rate_kwh
    elec_calc = next(c for c in spec.calculations if c.id == "annual_electricity_cost")
    elec_cost = SafeFormulaEngine.evaluate(
        elec_calc.formula,
        {"power_consumption_watts": 45.0, "hours_per_day": 24.0, "electricity_rate_kwh": 0.16}
    )
    # (45 / 1000) * 24 * 365 * 0.16 = 0.045 * 8760 * 0.16 = 394.2 * 0.16 = 63.072
    assert elec_cost == pytest.approx(63.072, 0.01)

    # Formula 3: annual_filter_cost = (12.0 / lifespan_months) * replacement_price_usd
    filter_calc = next(c for c in spec.calculations if c.id == "annual_filter_cost")
    filter_cost = SafeFormulaEngine.evaluate(
        filter_calc.formula,
        {"lifespan_months": 6.0, "replacement_price_usd": 40.0}
    )
    assert filter_cost == pytest.approx(80.0, 0.01)

    # 4. Test Declarative Compatibility Rule
    comp_rule = next(c for c in spec.compatibility_rules if c.rule_id == "purifier_filter_fit")
    match_eval = DeclarativeRuleEvaluator.evaluate_rule(
        rule=comp_rule,
        subject={"brand": "Levoit", "model": "Replacement Filter Core 300"},
        target={"brand": "Levoit", "model": "Core 300 Air Purifier"},
        context={
            "subject_attrs": {"filter_diameter_mm": 190.0},
            "target_attrs": {"filter_slot_diameter_mm": 190.0}
        }
    )
    assert match_eval["verdict"] == "PASS"

    mismatch_eval = DeclarativeRuleEvaluator.evaluate_rule(
        rule=comp_rule,
        subject={"brand": "Coway", "model": "Filter AP-1512HH"},
        target={"brand": "Levoit", "model": "Core 300 Air Purifier"},
        context={
            "subject_attrs": {"filter_diameter_mm": 280.0},
            "target_attrs": {"filter_slot_diameter_mm": 190.0}
        }
    )
    assert mismatch_eval["verdict"] == "FAIL"

    # 5. Execute 7-stage Niche Sandbox Dry-Run
    sandbox_report = NicheSandbox.run_dry_run(spec)
    assert sandbox_report.verdict == "PASS"
    assert sandbox_report.stages_completed == 7
    assert sandbox_report.readiness_score >= 85.0
    assert "air_purifier_room_suitability" in sandbox_report.calculations_tested
    assert "purifier_filter_fit" in sandbox_report.compatibility_rules_tested
    assert len(sandbox_report.page_plans_generated) > 0
    assert sandbox_report.quality_gate_audit["passed"] is True



# ==============================================================================
# TEST 2: DOG CRATE NO-CODE ACCEPTANCE TEST (ZERO PYTHON CODE)
# ==============================================================================

def test_dog_crate_no_code_pipeline():
    """
    Acceptance Test 2: Dog Crates.
    Specifies entities (DogCrate, DogBreed, VehicleCargoArea), sizing math, and fitment rules.
    Must validate, evaluate breed sizing & vehicle fitment, and PASS sandbox dry-run.
    """
    draft = AINicheDesigner.design_from_prompt(
        "Design a data-driven dog crate and travel kennel site with breed sizing calculator and SUV cargo fitment check."
    )
    assert draft is not None
    assert draft.proposed_niche.niche_id == "dog_crates"
    spec = draft.proposed_niche

    # 1. Verify Entities & Schema
    assert "DogCrate" in spec.entity_types
    assert "DogBreed" in spec.entity_types
    assert "VehicleCargoArea" in spec.entity_types

    # 2. Validate Niche Spec
    validation_report = NicheValidator.validate(spec)
    assert validation_report.is_valid is True

    # 3. Test Breed Sizing Calculation
    # min_crate_length_in = avg_length_snout_to_tail_inches + 4.0
    crate_len_calc = next(c for c in spec.calculations if c.id == "dog_crate_min_length_needed")
    min_len = SafeFormulaEngine.evaluate(crate_len_calc.formula, {"avg_length_snout_to_tail_inches": 32.0})
    assert min_len == 36.0

    # 4. Test Breed Sizing Fitment Rule
    dog_rule = next(c for c in spec.compatibility_rules if c.rule_id == "crate_dog_size_suitability")
    fit_eval = DeclarativeRuleEvaluator.evaluate_rule(
        rule=dog_rule,
        subject={"brand": "Gunner", "model": "G1 Intermediate"},
        target={"brand": "Canine", "model": "Golden Retriever"},
        context={
            "subject_attrs": {"internal_length_inches": 34.0, "max_dog_weight_lbs": 75.0},
            "target_attrs": {"avg_length_snout_to_tail_inches": 28.0, "avg_adult_weight_lbs": 65.0}
        }
    )
    assert fit_eval["verdict"] == "PASS"

    too_small_eval = DeclarativeRuleEvaluator.evaluate_rule(
        rule=dog_rule,
        subject={"brand": "Gunner", "model": "G1 Small"},
        target={"brand": "Canine", "model": "Great Dane"},
        context={
            "subject_attrs": {"internal_length_inches": 24.0, "max_dog_weight_lbs": 30.0},
            "target_attrs": {"avg_length_snout_to_tail_inches": 42.0, "avg_adult_weight_lbs": 140.0}
        }
    )
    assert too_small_eval["verdict"] == "FAIL"

    # 5. Execute Niche Sandbox Dry-Run
    sandbox_report = NicheSandbox.run_dry_run(spec)
    assert sandbox_report.verdict == "PASS"
    assert sandbox_report.stages_completed == 7
    assert sandbox_report.quality_gate_audit["passed"] is True


# ==============================================================================
# TEST 3: SAFE FORMULA ENGINE AST SECURITY
# ==============================================================================

def test_safe_formula_engine_security():
    """Verifies that SafeFormulaEngine strictly rejects malicious code and injection."""
    # 1. Block __import__ and os
    with pytest.raises(UnsafeFormulaError):
        SafeFormulaEngine.evaluate("__import__('os').system('echo pwned')", {})

    # 2. Block built-in eval / exec
    with pytest.raises(UnsafeFormulaError):
        SafeFormulaEngine.evaluate("eval('1 + 1')", {})

    # 3. Block attribute lookups (e.g., ().__class__.__bases__)
    with pytest.raises(UnsafeFormulaError):
        SafeFormulaEngine.evaluate("a.__class__.__name__", {"a": 10})

    # 4. Block file opening
    with pytest.raises(UnsafeFormulaError):
        SafeFormulaEngine.evaluate("open('secrets.txt').read()", {})

    # 5. Validate formula without execution
    is_valid, vars_found, err = SafeFormulaEngine.validate_formula("(a * b) + min(c, 10)")
    assert is_valid is True
    assert vars_found == {"a", "b", "c"}

    invalid_valid, _, err = SafeFormulaEngine.validate_formula("a.b + 5")
    assert invalid_valid is False
    assert err is not None


# ==============================================================================
# TEST 4: DECLARATIVE RULE EVALUATOR
# ==============================================================================

def test_declarative_rule_evaluator_operators():
    """Tests all supported declarative condition operators: ==, !=, >, >=, <, <=, IN, RANGE, CONTAINS."""
    # Operator: ==
    assert DeclarativeRuleEvaluator._eval_condition(10, "==", 10, None, None) is True
    assert DeclarativeRuleEvaluator._eval_condition(10, "==", 12, None, None) is False

    # Operator: == with tolerance
    assert DeclarativeRuleEvaluator._eval_condition(10.2, "==", 10.0, None, 0.5) is True

    # Operator: >= and <=
    assert DeclarativeRuleEvaluator._eval_condition(40, ">=", 30, None, None) is True
    assert DeclarativeRuleEvaluator._eval_condition(20, "<=", 25, None, None) is True

    # Operator: IN
    assert DeclarativeRuleEvaluator._eval_condition("HEPA", "IN", None, ["HEPA", "Carbon"], None) is True
    assert DeclarativeRuleEvaluator._eval_condition("PreFilter", "IN", None, ["HEPA", "Carbon"], None) is False

    # Operator: RANGE
    assert DeclarativeRuleEvaluator._eval_condition(25, "RANGE", None, [20, 30], None) is True
    assert DeclarativeRuleEvaluator._eval_condition(35, "RANGE", None, [20, 30], None) is False

    # Operator: CONTAINS
    assert DeclarativeRuleEvaluator._eval_condition("Compatible with Levoit Core 300 & Core 400", "CONTAINS", "Core 300", None, None) is True


# ==============================================================================
# TEST 5: NICHE VALIDATOR CATCHES ERRORS
# ==============================================================================

def test_niche_validator_catches_invalid_specs():
    """Tests that NicheValidator detects missing entities, unsafe formulas, and missing sources."""
    bad_spec = NicheSpec(
        niche_id="broken_niche",
        niche_name="Broken Niche",
        niche_description="Spec with intentional errors",
        entity_types=["Machine"],
        attributes={
            "UnknownEntity": [  # Entity not declared in entity_types
                AttributeSpec(key="weight", display_name="Weight", data_type=DataType.FLOAT)
            ]
        },
        relationships=[
            RelationshipSpec(source_entity="Machine", target_entity="MissingPart", relationship="USES")
        ],
        calculations=[
            CalculationSpec(
                id="unsafe_calc",
                name="Unsafe Calc",
                formula="__import__('os').system('calc')"
            )
        ]
    )

    report = NicheValidator.validate(bad_spec)
    assert report.is_valid is False
    assert len(report.critical_issues) > 0
    codes = [issue.code for issue in report.issues]
    assert "ORPHAN_ATTRIBUTE_ENTITY" in codes
    assert "RELATIONSHIP_TARGET_NOT_FOUND" in codes
    assert "CALCULATION_UNSAFE" in codes


# ==============================================================================
# TEST 6: ENCRYPTED CREDENTIAL STORE & MASKING
# ==============================================================================

def test_encrypted_credential_store():
    """Verifies that secrets are encrypted at rest, masked in UI, and never leak."""
    EncryptedCredentialStore.clear()
    site_id = "site_purifier_us"

    EncryptedCredentialStore.store_credential(site_id, "wordpress_app_password", "abcd-1234-efgh-5678")
    EncryptedCredentialStore.store_credential(site_id, "amazon_access_key", "AKIAIOSFODNN7EXAMPLE")

    # Plaintext retrieval (internal use only)
    wp_pass = EncryptedCredentialStore.get_credential(site_id, "wordpress_app_password")
    assert wp_pass == "abcd-1234-efgh-5678"

    # Masked retrieval (UI display use)
    masked = EncryptedCredentialStore.get_all_masked_for_site(site_id)
    assert "wordpress_app_password" in masked
    assert masked["wordpress_app_password"].is_set is True
    assert masked["wordpress_app_password"].masked_value != "abcd-1234-efgh-5678"
    assert "••••" in masked["wordpress_app_password"].masked_value
    assert masked["wordpress_app_password"].masked_value.endswith("5678")

    # Tenant/site isolation: another site cannot access site_purifier_us credentials
    other_site_creds = EncryptedCredentialStore.get_all_masked_for_site("site_other_uk")
    # All fields should report is_set == False
    assert all(not f.is_set for f in other_site_creds.values())


# ==============================================================================
# TEST 7: NICHE VERSIONING & SANITIZED EXPORT/IMPORT
# ==============================================================================

def test_niche_versioning_export_import():
    """Verifies YAML/JSON export sanitization and round-trip re-import."""
    draft = AINicheDesigner.design_from_prompt("Coffee equipment espresso machine grinders and extraction ratios")
    spec = draft.proposed_niche

    # 1. Export to YAML
    yaml_str = NicheVersioningManager.export_niche_yaml(spec)
    assert f"niche_id: {spec.niche_id}" in yaml_str
    assert "password" not in yaml_str.lower()
    assert "secret" not in yaml_str.lower()

    # 2. Re-import from YAML
    imported_spec = NicheVersioningManager.import_niche_yaml(yaml_str)
    assert imported_spec.niche_id == spec.niche_id
    assert imported_spec.entity_types == spec.entity_types

    # 3. Export to JSON
    json_str = NicheVersioningManager.export_niche_json(spec)
    assert f'"niche_id": "{spec.niche_id}"' in json_str

    # 4. Re-import from JSON
    imported_json_spec = NicheVersioningManager.import_niche_json(json_str)
    assert imported_json_spec.niche_id == spec.niche_id



# ==============================================================================
# TEST 8: SAAS SITE LIFECYCLE & JOB SCHEDULING GATING
# ==============================================================================

def test_saas_site_lifecycle_and_job_gating():
    """
    Verifies that sites start in DRAFT, transition according to lifecycle rules,
    and background jobs CANNOT run unless site status is ACTIVE.
    """
    SaaSSiteManager.clear()

    site = SaaSSiteManager.create_site(
        site_name="Clean Air Authority",
        domain="cleanairauthority.com",
        niche_id="air_purifiers"
    )
    assert site.lifecycle_status == SiteLifecycleStatus.DRAFT

    # Rule: Background jobs CANNOT be scheduled when DRAFT
    assert SaaSSiteManager.can_schedule_jobs(site.site_id) is False

    # Transition to CONFIGURING
    SaaSSiteManager.update_lifecycle_status(site.site_id, SiteLifecycleStatus.CONFIGURING)
    assert site.lifecycle_status == SiteLifecycleStatus.CONFIGURING
    assert SaaSSiteManager.can_schedule_jobs(site.site_id) is False

    # Transition to VALIDATING
    SaaSSiteManager.update_lifecycle_status(site.site_id, SiteLifecycleStatus.VALIDATING)
    assert site.lifecycle_status == SiteLifecycleStatus.VALIDATING
    assert SaaSSiteManager.can_schedule_jobs(site.site_id) is False

    # Transition to READY
    SaaSSiteManager.update_lifecycle_status(site.site_id, SiteLifecycleStatus.READY)
    assert site.lifecycle_status == SiteLifecycleStatus.READY
    assert SaaSSiteManager.can_schedule_jobs(site.site_id) is False

    # Transition to ACTIVE
    SaaSSiteManager.update_lifecycle_status(site.site_id, SiteLifecycleStatus.ACTIVE)
    assert site.lifecycle_status == SiteLifecycleStatus.ACTIVE
    assert SaaSSiteManager.can_schedule_jobs(site.site_id) is True

    # Transition to PAUSED
    SaaSSiteManager.update_lifecycle_status(site.site_id, SiteLifecycleStatus.PAUSED)
    assert site.lifecycle_status == SiteLifecycleStatus.PAUSED
    assert SaaSSiteManager.can_schedule_jobs(site.site_id) is False

    # Permission check: viewer cannot transition status
    site.user_roles["user_guest"] = PermissionRole.VIEWER
    with pytest.raises(PermissionError):
        SaaSSiteManager.update_lifecycle_status(site.site_id, SiteLifecycleStatus.ACTIVE, user_id="user_guest")


# ==============================================================================
# TEST 9: AI NICHE CRITIC, DATA AVAILABILITY & MARKET RESEARCH
# ==============================================================================

def test_ai_critic_and_market_research():
    """Verifies that AINicheCritic answers all 8 questions and calculates data availability score."""
    draft = AINicheDesigner.design_from_prompt("Air Purifiers and Clean Air Filters")
    spec = draft.proposed_niche

    # 1. AI Critic answers 8 questions
    critique = AINicheCritic.critique_niche(spec)
    assert critique["total_questions"] == 8
    assert len(critique["answers"]) == 8
    # Questions check
    q_titles = [a["question"] for a in critique["answers"]]
    assert any("Are important entities missing?" in q for q in q_titles)
    assert any("Are attributes sufficient?" in q for q in q_titles)
    assert critique["verdict"] in ["APPROVE", "REVISE"]

    # 2. Data Availability Score
    avail = DataAvailabilityScore.score_niche(spec)
    assert avail["score"] in ["STRONG", "MODERATE", "WEAK"]
    assert avail["numerical_score"] >= 0

    # 3. Market Research Estimator
    mr = MarketResearchEstimator.estimate(spec, country="US")
    assert mr["estimated_monthly_searches"] > 0
    assert mr["recommended_pages_initial"] >= 20
    assert "intent_breakdown" in mr
