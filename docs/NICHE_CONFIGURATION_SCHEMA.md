# Niche Configuration Schema Specification (`NicheSpec`)

## 1. Specification Overview

`NicheSpec` is the canonical, declarative data contract that defines an entire programmatic authority website without requiring custom Python niche adapters. It supports lossless JSON and YAML serialization and full version tracking.

---

## 2. Supported Data Types (`DataType`)

Every attribute modeled in a niche must adhere to one of the 12 verified types:

| Data Type | Allowed Units | Validation & Parsing Behavior |
|---|---|---|
| `STRING` | None | Free-form textual descriptions, model numbers, identifiers |
| `INTEGER` | `count`, `qty`, `items` | Strictly integer numerical values |
| `FLOAT` | Dimension, power, energy units | Decimal floating-point numbers |
| `BOOLEAN` | `True` / `False` | Binary toggles (e.g., `is_hepa_certified`) |
| `ENUM` | User-defined values | Restricted choice list (e.g., `["HEPA", "Carbon", "PreFilter"]`) |
| `DATE` | ISO-8601 | Standard date strings (`YYYY-MM-DD`) |
| `URL` | Web URI | Verified external links and datasheets |
| `MONEY` | `USD`, `EUR`, `GBP`, `VND`, `CAD`, `AUD`, `$`, `€`, `£` | Currency values with precision 2 decimals |
| `DIMENSION` | `in`, `mm`, `cm`, `m`, `ft`, `sqft`, `sqm`, `cu_ft`, `cu_in`, `L` | Spatial measurements automatically normalized |
| `POWER` | `W`, `kW`, `mW`, `hp` | Electrical wattage ratings |
| `ENERGY` | `Wh`, `kWh`, `J`, `BTU`, `mAh`, `Ah` | Battery and energy storage capacities |
| `PERCENTAGE` | `%`, `pct` | Ratios from 0.0 to 100.0 |

---

## 3. Safe Formula Engine Grammar (`SafeFormulaEngine`)

Calculations are evaluated using Python's `ast` module in strict read-only evaluation mode.

### Allowed Arithmetic Operators
- Addition (`+`), Subtraction (`-`), Multiplication (`*`), Division (`/`)
- Floor Division (`//`), Modulo (`%`), Exponentiation (`**`)
- Unary Negation (`-x`), Unary Positive (`+x`)

### Whitelisted Mathematical Functions
- `min(*args)`: Minimum of values.
- `max(*args)`: Maximum of values.
- `round(number, digits)`: Precision rounding.
- `abs(x)`: Absolute value.
- `sqrt(x)`: Square root.
- `ceil(x)` / `floor(x)`: Ceiling and floor.
- `log(x, [base])`: Logarithmic scaling.

### Strictly Forbidden AST Constructs
- Function definitions (`def`), lambdas, class declarations.
- Direct attribute lookups (`x.__class__`, `os.system`).
- Variable assignments, imports, eval, exec, and filesystem operations (`open()`).

---

## 4. Declarative Compatibility Rules (`CompatibilityRuleSpec`)

Compatibility rules evaluate whether two entities (e.g. `Filter` and `AirPurifier`, or `DogCrate` and `DogBreed`) physically or electrically function together.

### Condition Structure
```json
{
  "subject_attribute": "filter_diameter_mm",
  "operator": "==",
  "target_attribute": "filter_slot_diameter_mm",
  "tolerance": 2.0
}
```

### Supported Condition Operators
- `==`: Equality within optional numeric `tolerance`.
- `!=`: Strict inequality.
- `>` and `>=`: Greater than / Greater than or equal (with optional tolerance).
- `<` and `<=`: Less than / Less than or equal (with optional tolerance).
- `IN`: Membership test within an array of allowed constants.
- `RANGE`: Bounded interval test `[min_val, max_val]` with tolerance padding.
- `CONTAINS`: Substring containment (case-insensitive).

---

## 5. Canonical YAML Example: Air Purifiers

```yaml
niche_id: air_purifiers
niche_name: Air Purifiers & Clean Air
niche_description: Authoritative technical data on air purifiers, CADR ratings, and HEPA filter replacements.
version: 1.0.0
risk_profile: LOW
capabilities:
  - PRODUCT_DATABASE
  - TECHNICAL_SPECS
  - COMPATIBILITY
  - CALCULATION
  - COMPARISON
  - AFFILIATE_COMMERCE
entity_types:
  - AirPurifier
  - Filter
  - Room
  - Pollutant
attributes:
  AirPurifier:
    - key: cadr_smoke_cfm
      display_name: CADR Smoke Rating
      data_type: FLOAT
      unit: cfm
      required: true
      critical: true
      preferred_source_type: CERTIFICATION
    - key: power_consumption_watts
      display_name: Electrical Consumption
      data_type: POWER
      unit: W
      required: true
      critical: true
      preferred_source_type: MANUFACTURER
    - key: filter_slot_diameter_mm
      display_name: Filter Chamber Diameter
      data_type: DIMENSION
      unit: mm
      required: true
      critical: true
      preferred_source_type: MANUFACTURER
  Filter:
    - key: filter_diameter_mm
      display_name: Outer Diameter
      data_type: DIMENSION
      unit: mm
      required: true
      critical: true
      preferred_source_type: MANUFACTURER
    - key: lifespan_months
      display_name: Operational Lifespan
      data_type: FLOAT
      unit: months
      required: true
      critical: false
      preferred_source_type: MANUFACTURER
    - key: replacement_price_usd
      display_name: Replacement Price
      data_type: MONEY
      unit: USD
      required: true
      critical: false
      preferred_source_type: RETAILER
calculations:
  - id: air_purifier_room_suitability
    name: AHAM CADR 2/3 Room Area Match
    formula: cadr_smoke_cfm * 1.5
    output_unit: sqft
    required_variables:
      - cadr_smoke_cfm
  - id: annual_electricity_cost
    name: Annual Electrical Operating Cost
    formula: (power_consumption_watts / 1000.0) * hours_per_day * 365.0 * electricity_rate_kwh
    output_unit: USD
    required_variables:
      - power_consumption_watts
      - hours_per_day
      - electricity_rate_kwh
compatibility_rules:
  - rule_id: purifier_filter_fit
    name: Filter Slot Physical Compatibility
    subject_type: Filter
    target_type: AirPurifier
    conditions:
      - subject_attribute: filter_diameter_mm
        operator: ==
        target_attribute: filter_slot_diameter_mm
        tolerance: 2.0
    pass_verdict: PASS
    pass_status: EXACT_FIT
    fail_verdict: FAIL
    fail_status: DOES_NOT_FIT
    explanation_pass: Filter dimensions fit inside air purifier enclosure.
    explanation_fail: Filter diameter does not match air purifier slot.
source_policies:
  - source_type: CERTIFICATION
    priority: 1
    allowed_for_critical_facts: true
    freshness_interval_days: 730
  - source_type: MANUFACTURER
    priority: 2
    allowed_for_critical_facts: true
    freshness_interval_days: 365
page_types:
  - page_type_id: compatibility
    name: Filter Replacement Fitment Guide
    primary_intent: COMPATIBILITY
    required_entities:
      - AirPurifier
      - Filter
  - page_type_id: comparison
    name: Room Sizing & CADR Comparison
    primary_intent: COMPARISON
    required_entities:
      - AirPurifier
      - Room
```
