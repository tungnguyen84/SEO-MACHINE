# Architectural Audit & Core Purity Report: Generic AI Niche Designer
**Investigation: Domain-Specific Knowledge Elimination, Provenance Governance & Core Freezing**
*Date: 2026-09-26 | Environment: OpenSEO Multi-Tenant Cloud / PostgreSQL 16 Staging*

---

## 1. Executive Summary & Root Cause Investigation

During user acceptance review of the Home Dehumidifiers vertical, an audit was triggered to determine whether OpenSEO genuinely generalized to arbitrary, unseen niches or whether domain-specific knowledge had been hardcoded inside generic-looking modules.

### Findings
1. **Critical Coupling Identified**: `core/niche_builder/ai_designer.py` previously contained hidden keyword routing:
   ```python
   # Previous implementation in ai_designer.py (NOW REMOVED):
   if any(w in clean for w in ["air purifier", "purifier", "cadr", ...]):
       spec = cls._design_air_purifier_niche()
   elif any(w in clean for w in ["dog crate", "crate", ...]):
       spec = cls._design_dog_crate_niche()
   elif any(w in clean for w in ["dehumidifier", "humidity", "moisture", ...]):
       return NicheSpec(niche_id="home_dehumidifiers", ...)
   ```
2. **Hidden Fixtures in Generic Sandbox**: `core/niche_builder/sandbox.py` contained hardcoded attribute string checks (`val = 50.0 * i if "cadr" in attr_spec.key...`).
3. **Verdict**: **The previous Dehumidifier acceptance test was partially hardcoded.** The ontology, 13 attributes, and DOE/AHAM formulas were hardcoded in `ai_designer.py` rather than synthesized through generic reasoning.

### Remediation Executed
- **Zero Keyword Routing in Core**: All domain keyword routing branches, entity presets, and attribute dictionaries were completely purged from `core/niche_builder/ai_designer.py` and `core/niche_builder/sandbox.py`.
- **Explicit Template Registry**: Pre-configured declarative reference specifications were relocated to `core/niche_templates/` (`air_purifiers.py`, `dog_crates.py`, `dehumidifiers.py`), satisfying Core Purity Rule 2 ("isolated strictly in explicit template/test/adapter directories").
- **Pure Generic Semantic Synthesizer**: Replaced with a syntactic, linguistic parser extracting primary subjects, environments, components, power, flow, sizing, and cost attributes directly from user grammar without domain lookup tables.

---

## 2. Comprehensive Codebase Domain Knowledge Audit

Every occurrence of domain terms across `core/` was scanned and classified:

| Target File | Scanned Domain Terms Found | Classification | Action Taken |
| :--- | :--- | :--- | :--- |
| `core/niche_builder/ai_designer.py` | `dehumidifier`, `pints`, `cadr`, `air purifier`, `dog crate`, `dog breed`, `basement`, `humidity` (42 instances) | **INVALID GENERIC-CORE DOMAIN KNOWLEDGE** | **Completely purged.** Replaced with pure generic syntactic parser. Total occurrences now: **0**. |
| `core/niche_builder/sandbox.py` | `cadr` (Line 103) | **INVALID GENERIC-CORE DOMAIN KNOWLEDGE** | **Purged.** Replaced with generic data type check (`DataType.DIMENSION`, `DataType.POWER`). |
| `core/niche_adapters/vehicle_camping.py` | `vehicle`, `camping`, `fridge`, `subaru`, `dometic` | **VALID NICHE ADAPTER** | Preserved in explicit adapter subsystem. |
| `core/niche_adapters/coffee_equipment.py` | `coffee`, `espresso`, `grinder`, `portafilter` | **VALID NICHE ADAPTER** | Preserved in explicit adapter subsystem. |
| `core/niche_adapters/workshop_tools.py` | `workshop`, `battery platform`, `dewalt`, `milwaukee` | **VALID NICHE ADAPTER** | Preserved in explicit adapter subsystem. |
| `core/engine/calculation.py` | `solar` (solar charging formula) | **LEGACY ENGINE UTILITY** | Preserved as baseline math utility function. |
| `core/niche_templates/air_purifiers.py` | `air purifier`, `cadr`, `hepa` | **NICHE TEMPLATE** | Explicit reference template directory. |
| `core/niche_templates/dog_crates.py` | `dog crate`, `dog breed`, `kennel` | **NICHE TEMPLATE** | Explicit reference template directory. |
| `core/niche_templates/dehumidifiers.py` | `dehumidifier`, `pints`, `basement` | **NICHE TEMPLATE** | Explicit reference template directory. |
| `tests/*.py` | Multiple test fixtures | **TEST FIXTURE** | Valid test suites verifying declarative execution. |

---

## 3. Reclassification of Previous Dehumidifier Test

A rigorous audit of the 13 attributes and formulas from the previous Home Dehumidifier acceptance test was conducted:

| Concept / Item | Previous Presentation | Genuine Provenance | Audit Verdict |
| :--- | :--- | :--- | :--- |
| `capacity_pints_day` | "AI-Synthesized" | Hardcoded dictionary in `ai_designer.py` | **HARDCODED FIXTURE** |
| `recommended_room_sqft` | "AI-Synthesized" | Hardcoded dictionary in `ai_designer.py` | **HARDCODED FIXTURE** |
| `power_consumption_watts` | "AI-Synthesized" | Hardcoded dictionary in `ai_designer.py` | **HARDCODED FIXTURE** |
| `energy_factor_l_kwh` | "AI-Synthesized" | Hardcoded dictionary in `ai_designer.py` | **HARDCODED FIXTURE** |
| `energy_star_certified` | "AI-Synthesized" | Hardcoded dictionary in `ai_designer.py` | **HARDCODED FIXTURE** |
| `drainage_method` | "AI-Synthesized" | Hardcoded dictionary in `ai_designer.py` | **HARDCODED FIXTURE** |
| `has_internal_pump` | "AI-Synthesized" | Hardcoded dictionary in `ai_designer.py` | **HARDCODED FIXTURE** |
| `water_tank_capacity_pints`| "AI-Synthesized" | Hardcoded dictionary in `ai_designer.py` | **HARDCODED FIXTURE** |
| `min_operating_temp_f` | "AI-Synthesized" | Hardcoded dictionary in `ai_designer.py` | **HARDCODED FIXTURE** |
| `auto_defrost` | "AI-Synthesized" | Hardcoded dictionary in `ai_designer.py` | **HARDCODED FIXTURE** |
| `noise_level_db` | "AI-Synthesized" | Hardcoded dictionary in `ai_designer.py` | **HARDCODED FIXTURE** |
| `washable_filter` | "AI-Synthesized" | Hardcoded dictionary in `ai_designer.py` | **HARDCODED FIXTURE** |
| `retail_price_usd` | "AI-Synthesized" | Hardcoded dictionary in `ai_designer.py` | **HARDCODED FIXTURE** |
| **DOE 2019 Standard References** | "Discovered" | Hardcoded in `ai_designer.py` string templates | **HARDCODED INVENTED STANDARD** |
| **AHAM Sizing Matrix** | "Calculated" | Hardcoded multiplier `* 50.0` in `ai_designer.py` | **HARDCODED INVENTED STANDARD** |
| **Pump Vertical Lift (15-16 ft)** | "Source Fact" | Hardcoded in test fixture | **HARDCODED FIXTURE** |
| **Temperature Floor (41°F)** | "Source Fact" | Hardcoded in test fixture | **HARDCODED FIXTURE** |
| **$0.16/kWh Tariff** | "EIA Average" | Fixed constant in test runner | **UNVERIFIED ASSUMPTION** |

---

## 4. Verification of Electricity Cost Attribution ($0.16/kWh)

- **Previous Claim**: "$0.16/kWh average US electricity price according to EIA."
- **Audit Result**: No live API call or verified EIA publication dataset was retrieved during runtime. \$0.16 was merely an unverified baseline constant.
- **Remediation**:
  - The \$0.16/kWh figure is strictly labeled as **`ASSUMPTION`** in the Claim Inspector.
  - The UI and API must disclose: *"Electricity running cost calculations use a baseline assumption of \$0.16/kWh (US residential average model). Local utility tariffs vary significantly by state and utility provider."*

---

## 5. Verification of Suitability Scoring (Categorical vs Heuristic)

- **Previous Result**: Frigidaire 50-Pint ➔ `100% EXCELLENT`.
- **Audit Result**: "100%" implies mathematical perfection or certainty that cannot be defended empirically. Dehumidification sizing involves variable building envelopes, infiltration rates, humidity swings, and ceiling heights.
- **Remediation**:
  - Heuristic percentage scores are replaced by defensible categorical suitability verdicts:
    1. **`STRONG_MATCH`**: Specifications comfortably exceed all operating requirements with safety margin.
    2. **`MATCH_WITH_CONDITIONS`**: Meets primary capacity but requires specific environmental provisions (e.g. gravity drain or ambient > 50°F).
    3. **`WEAK_MATCH`**: Borderline capacity; risk of continuous non-stop cycling under peak loads.
    4. **`NOT_SUITABLE`**: Insufficient capacity or missing mandatory hardware features (e.g. lacks pump when vertical lift is needed).
    5. **`UNKNOWN`**: Missing required device or environmental parameters. **`UNKNOWN` is treated as a valid, honest, and desirable product response.**

---

## 6. Formula & Rule Provenance Governance

In compliance with Sections 5, 6, and 7:
1. **No Invented Authoritative Standards**: The generic AI designer may propose calculations and rules, but they are strictly flagged with `provenance_type="MODEL_PROPOSED"`.
2. **Provenance Classes**:
   - `OFFICIAL_STANDARD`: Verified against published governmental or industry standards (DOE, EPA, AHAM, AKC).
   - `MANUFACTURER`: Sourced directly from official technical datasheets and manuals.
   - `INDEPENDENT`: Verified by accredited third-party testing laboratories.
   - `DERIVED`: Mathematically derived from verified physical relationships.
   - `USER_DEFINED`: Explicitly configured by the human operator in the No-Code UI.
   - `MODEL_PROPOSED`: Proposed by the AI designer; **cannot become verified or authoritative without explicit source citation.**

---

## 7. Frozen Generic Core Cryptographic Hashes

To guarantee that blind tests do not introduce hidden domain logic, the generic core files were hashed using SHA-256 before testing began:

- **Recorded in**: `docs/BLIND_TEST_CORE_HASHES_BEFORE.json`
- **Total Tracked Generic Files**: 18 files across `core/niche_builder/`, `core/writer/`, `core/planner/`, `core/entities/`, and `core/research/`.
- **Frozen Combined Core SHA-256**: `42ae4570d6a918a41d5df21017a5351ef2341e599087c0c07487de78979e9ebb`
- **Blind Test Immutability Requirement**: Zero changes to these 18 files throughout the Aquarium and Sewing Machine blind tests.
