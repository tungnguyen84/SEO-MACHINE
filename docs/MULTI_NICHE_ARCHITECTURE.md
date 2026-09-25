# OpenSEO Multi-Site & Multi-Niche Data Authority SaaS Architecture

## Executive Summary

OpenSEO has transitioned from a single-niche reference implementation (Vehicle Camping & Overlanding) to a **Multi-Site, Multi-Niche Data Authority SaaS Platform**. The platform is designed around a strict decoupling model: the **Core Engine** is 100% agnostic to any specific vertical, product category, or physical ontology, while domain-specific knowledge, formulas, compatibility rules, entity hierarchies, and prompt differentiators are encapsulated inside modular **Niche Adapters**.

---

## 1. Architectural Boundaries: Core Engine vs. Niche Adapters

```
+---------------------------------------------------------------------------------------+
|                                    CORE SaaS ENGINE                                   |
|                                                                                       |
|  +---------------------+   +-----------------------+   +---------------------------+  |
|  |   Entity Model      |   |  Freshness Engine     |   |   Page Planner            |  |
|  |  (Generic Products, |   |  (Static / Semi-Dyn / |   |  (Jaccard Clustering,     |  |
|  |   Attrs, Offers)    |   |   Dynamic Policies)   |   |   Information Gain)       |  |
|  +----------+----------+   +-----------+-----------+   +-------------+-------------+  |
|             |                          |                             |                |
|  +----------+----------+   +-----------+-----------+   +-------------+-------------+  |
|  | Calculation Engine  |   | Compatibility Engine  |   | Grounded Writer           |  |
|  | (Generic Formula    |   | (Dynamic Evaluator    |   | (Data-First Generation,   |  |
|  |  Execution Engine)  |   |  Rule Matching)       |   |  Strict Claim Citation)   |  |
|  +----------+----------+   +-----------+-----------+   +-------------+-------------+  |
|             |                          |                             |                |
|  +----------+----------+   +-----------+-----------+   +-------------+-------------+  |
|  | Quality Gate        |   | Multi-Tenant Site     |   | Publisher Engine          |  |
|  | (Anti-Hallucination |   | Manager (Scoping WP,  |   | (Idempotent Draft Sync,   |  |
|  |  Evidence Provenance|   | GSC, Affiliate Tags)  |   |  PostgreSQL / SQLite)     |  |
|  +---------------------+   +-----------------------+   +---------------------------+  |
+-------------------------------------------+-------------------------------------------+
                                            |
                         NicheAdapter Protocol / Interface
                                            |
      +-------------------------------------+-----------------------------------+
      |                                     |                                   |
+-----+-------------------+   +-------------+-----------+   +-------------------+-----+
|  VehicleCampingAdapter  |   |  CoffeeEquipmentAdapter |   |  WorkshopToolsAdapter   |
|  - Dimensions / Cargo   |   |  - 58mm / 54mm Baskets  |   |  - Tool x Battery Fits  |
|  - 12V Auxiliary Amps   |   |  - Brew Ratio Formulas  |   |  - Cut Speed / Torque   |
|  - Fridge Autonomy Math |   |  - Extraction Yield     |   |  - Blade Compatibility  |
+-------------------------+   +-------------------------+   +-------------------------+
                                            |
                              +-------------+-------------+
                              | ConfigDrivenNicheAdapter  |
                              | (Declarative niche.yaml)  |
                              +---------------------------+
```

### Core Engine Guarantees
1. **Zero Hardcoded Domain Logic**: The core engine contains `INVALID_CORE_COUPLING = 0`. No vehicle terms (`cargo`, `hatch`, `subaru`, `outback`), coffee terms (`basket`, `brew_ratio`), or tool terms (`battery_platform`, `saw`) exist anywhere in `core/`.
2. **Dynamic Extension**: When a niche adapter registers with `NicheRegistry`, it dynamically injects:
   - Entity type definitions and required specification keys.
   - Dynamic compatibility rules (`CompatibilityRule`).
   - Mathematical calculations (`CalculationDefinition`).
   - Freshness policy configurations (`AttributeDefinition`).
   - Clustering token differentiators and semantic synonyms.
   - SERP competitor domain categorizations.
3. **Pluggable Normalization**: Normalizer metaclasses (`NormalizerMeta`) dynamically delegate domain-specific normalization methods to registered niche adapters.

---

## 2. Multi-Tenant Site Isolation (`SiteProfile`)

Each website managed by OpenSEO operates under a strictly isolated `SiteProfile`:

```python
class SiteProfile(BaseModel):
    site_id: str                      # e.g., "site_outback_overland_us"
    domain: str                       # e.g., "outbackoverland.com"
    niche_id: str                     # e.g., "vehicle_camping"
    wp_base_url: str                  # Isolated WordPress endpoint
    wp_app_username: str              # Scoped WP application user
    wp_app_password: str              # Scoped WP application token
    gsc_site_url: str                 # Scoped Google Search Console property
    affiliate_tag: str                # Scoped Amazon / merchant affiliate tracking tag
    default_author_id: int = 1
    post_status: str = "draft"        # Safe default: drafts only
```

### Tenant Isolation Enforcement
- **Affiliate Tag Scoping**: Merchant offer generation replaces affiliate tracking tags per tenant site (`tag={site_profile.affiliate_tag}`). No revenue cross-contamination.
- **WordPress Credential Scoping**: `WordPressClient.from_site_profile(site_profile)` binds all API requests to the tenant's isolated authentication credentials.
- **GSC Property Scoping**: Search performance telemetry queries are strictly isolated to `site_profile.gsc_site_url`.
- **Database Ownership**: In multitenant tables, entities, pages, and audit logs are scoped by `site_id` and `niche_id`.
- **Background Jobs**: Asynchronous crawler, refresh, and publishing queues are parameterized by `site_id`.

---

## 3. Capability System

Adapters declare fine-grained capabilities using the `Capability` enum:

| Capability | Description | Enabled When |
| :--- | :--- | :--- |
| `COMPATIBILITY` | Physical, electrical, or functional fitment checks | Niche involves two interacting physical entities |
| `CALCULATION` | Deterministic mathematical formulas and physics modelling | Engineering or metric relationships exist |
| `PRODUCT_DATABASE` | Entity storage with verified attributes and evidence claims | Hardware, appliances, gear, or consumables exist |
| `TECHNICAL_SPECS` | Verified dimensions, capacities, tolerances, and pinouts | Rigorous datasheet extraction is required |
| `AFFILIATE_COMMERCE` | Price tracking, merchant offers, and affiliate links | Monetization via affiliate programs |
| `FORUM_MINING` | Ingestion of real-world user field data from community forums | Unofficial user build data is relevant |

---

## 4. The Niche Adapter Interface (`NicheAdapter`)

All niche adapters implement the abstract base class `core.niche_adapters.base_adapter.NicheAdapter`:

```python
class NicheAdapter(ABC):
    @property
    @abstractmethod
    def niche_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def capabilities(self) -> List[Capability]: ...

    @property
    def risk_profile(self) -> RiskProfile: ...

    @property
    def entity_types(self) -> List[str]: ...

    @property
    def attribute_definitions(self) -> Dict[str, List[AttributeDefinition]]: ...

    @property
    def compatibility_rules(self) -> List[CompatibilityRule]: ...

    @property
    def calculations(self) -> List[CalculationDefinition]: ...

    @property
    def intent_taxonomy(self) -> Dict[str, List[str]]: ...

    @property
    def blueprints(self) -> List[PageBlueprint]: ...

    def get_cluster_differentiators(self) -> Set[str]: ...
    def get_domain_stop_words(self) -> Set[str]: ...
    def get_semantic_synonyms(self) -> Dict[str, str]: ...
    def get_known_competitors(self) -> Dict[str, str]: ...
    def get_known_brands(self) -> List[str]: ...
    def get_required_specs(self, entity_type: str) -> List[str]: ...
    def should_cluster(self, fp1: Set[str], fp2: Set[str], jaccard: float) -> bool: ...
    def get_lead_summary(self, primary_entity: Dict[str, Any], model: str, keyword: str) -> str: ...
    def seed_default_entities(self) -> int: ...
```

---

## 5. Declarative Config-Driven Niches (`niche.yaml`)

New niches can be declared entirely in YAML without writing any Python code using `ConfigDrivenNicheAdapter`:

```yaml
niche_id: "home_solar"
name: "Home Solar & Battery Backup Systems"
description: "Residential solar panels, hybrid inverters, and home battery storage."
risk_profile: "MEDIUM"

capabilities:
  - "COMPATIBILITY"
  - "CALCULATION"
  - "PRODUCT_DATABASE"
  - "TECHNICAL_SPECS"
  - "AFFILIATE_COMMERCE"

entity_types:
  - "solar_panel"
  - "inverter"
  - "home_battery"

attribute_definitions:
  solar_panel:
    - key: "rated_wattage_stc"
      display_name: "STC Rated Wattage"
      data_type: "numeric"
      unit_type: "W"
      required: true
      freshness_policy: "STATIC"
  home_battery:
    - key: "usable_capacity_kwh"
      display_name: "Usable Energy Storage"
      data_type: "numeric"
      unit_type: "kWh"
      required: true
      freshness_policy: "SEMI_DYNAMIC"

calculations:
  - id: "daily_solar_generation"
    name: "Daily Solar Energy Yield"
    formula_description: "Calculates estimated daily kWh generation based on panel wattage and sun hours."
    formula: "panel_wattage * peak_sun_hours * system_efficiency / 1000.0"

compatibility_rules:
  - rule_id: "panel_inverter_voltage_fit"
    name: "Panel String to Inverter MPPT Voltage Fit"
    subject_type: "solar_panel"
    target_type: "inverter"
```

The `NicheCreationWizard` provides an automated scaffolding CLI to validate, instantiate, and register any YAML-defined niche into the running OpenSEO runtime.
