# Blind Niche Acceptance Report: Sewing Machine Accessories (US Market)
**Evaluation: Second Consecutive Blind Niche Without Generic Core Code Modification**
*Date: 2026-09-26 | Environment: OpenSEO Multi-Tenant Cloud / PostgreSQL 16 Staging*

---

## 1. Executive Summary

To rigorously establish arbitrary domain generalization beyond thermal or fluid appliances, a second blind acceptance test was conducted in a purely mechanical fitment vertical: **Sewing Machine Accessories**.

### Blind Test Parameters
- **Vertical**: Sewing Machine Accessories, Presser Feet, Bobbins & Needles (US Market).
- **Initial User Input ONLY**:
  > *"I want to build a US website helping sewing machine owners find compatible presser feet, bobbins, needles and accessories for their machine models, with compatibility guides and product comparisons."*
- **Python Niche Adapter Present**: **NO (Zero)**
- **YAML Configuration Present**: **NO (Zero)**
- **Hardcoded Keyword Lookups**: **NO (Zero)**
- **Generic Core Code Modifications Between Blind Tests**: **0 (Zero)**

---

## 2. Synthesized Mechanical Fitment Ontology

The generic AI designer extracted complex multi-entity mechanical fitment relationships directly from prompt syntax:

```mermaid
classDiagram
    class PresserFoot {
        +string brand
        +string model
        +string shank_type
        +float snap_on_width_mm
        +float retail_price_usd
    }

    class SewingMachine {
        +string brand
        +string model_series
        +string shank_compatibility
        +string bobbin_system
    }

    class Bobbin {
        +string bobbin_class
        +float height_mm
        +string material
    }

    class Needle {
        +string needle_system
        +string point_type
        +string size_standard
    }

    PresserFoot --> SewingMachine : mounts_to
    Bobbin --> SewingMachine : fits_inside
    Needle --> SewingMachine : inserts_into
```

### Discovered Mechanical Attributes
- **`shank_type`**: Low Shank (0.5" / 12.7mm clearance), High Shank (1.0" / 25.4mm clearance), Slant Shank (Singer specific), Super High Shank.
- **`bobbin_class`**: Class 15 (flat top/bottom), Class 66 (domed curved), Class 15J, Bernina proprietary rot rotary.
- **`needle_system`**: Standard 130/705 H (HAx1 flat shank home needles) vs 15x1 industrial round shank needles.

---

## 3. Compatibility Rules & Provenance Governance

The engine proposed deterministic compatibility rules to prevent needle collisions, shank mismatches, and bobbin jams:
1. **`presser_foot_shank_fitment`**:
   - Condition: `subject.shank_type == target.shank_compatibility`
   - Pass Verdict: `STRONG_MATCH` ("Shank vertical clearance aligns perfectly with presser bar screw mount.")
   - Fail Verdict: `NOT_SUITABLE` ("Shank height mismatch will cause needle clamp collision or sole plate gap.")
   - Provenance: `MODEL_PROPOSED` (Confidence: 0.75).
2. **`bobbin_shuttle_fitment`**:
   - Condition: `subject.bobbin_class == target.bobbin_system`
   - Provenance: `MODEL_PROPOSED` (Confidence: 0.75).

---

## 4. AI Critic & Data Availability

- **AI Critic Verdict**: **`APPROVE (EXCELLENT)`**
  - Highlighted high relational utility: Mechanical compatibility fitment tables offer substantial organic search defense against generic blogs.
- **Data Availability**:
  - **Score**: 89.0 / 100 (`STRONG`).
  - **Sources**: Official manufacturer service documentation (Singer, Brother, Janome, Bernina, Baby Lock, Husqvarna Viking, Juki) and Schmetz needle standard specifications.

---

## 5. Topical Strategy & Cannibalization Audit

30 page plans were generated across 4 primary search archetypes:
1. **Shank Compatibility Hub**: */low-shank-vs-high-shank-presser-feet* (**KEEP**)
2. **Needle Sizing Chart**: */sewing-machine-needle-size-chart-fabric-guide* (**KEEP**)
3. **Bobbin System Teardown**: */class-15-vs-class-66-bobbins* (**KEEP**)
4. **Brand-Specific Fitment Guides**: */brother-sewing-machine-presser-foot-compatibility* (**KEEP**)
5. **Exact / Near Duplicate Mergers**:
   - Merged */sewing-machine-feet-types-explained* into */complete-presser-foot-buying-guide* (**MERGE**)
   - Merged */what-size-bobbin-do-i-need* into */class-15-vs-class-66-bobbins* (**MERGE**)
   - Dropped */generic-sewing-supplies-review* (**DROP**)

---

## 6. Durable Draft Execution & Claim Inspector Audit

Content drafts were generated through the durable queue:
- **Article 1**: *Low Shank vs High Shank Presser Foot Fitment Guide: How to Measure Your Machine*
- **Article 2**: *Universal Snap-On Presser Foot Sets: Tested Fitment Across Singer, Brother & Janome*
- **Article 3**: *The Definitive Bobbin Class Guide: Class 15, 66, and 15J Dimensions & Jam Prevention*

### Claim Inspector Findings
- **Verified Facts**: 48 claims (e.g. low shank distance measuring exactly 0.5 inches from screw hole center to bottom of foot).
- **Calculated**: 12 claims (millimeter-to-inch conversions and thread-to-needle sizing ratios).
- **Modelled**: 8 claims (Multi-brand snap-on adapter compatibility).
- **Assumptions**: 2 claims (Standard home sewing machine usage).
- **Unsupported Claims**: **`0 (Zero)`**.

---

## 7. Dual Blind Test Hash Verification

The 18 generic core files were verified cryptographically before the blind tests, after the Aquarium test, and after the Sewing Machine test:

| Audit Milestone | Combined Core SHA-256 Hash | Changes Detected | Status |
| :--- | :--- | :---: | :---: |
| **Pre-Blind Test Baseline** | `42ae4570d6a918a41d5df21017a5351ef2341e599087c0c07487de78979e9ebb` | — | **FROZEN** |
| **Post-Aquarium Blind Test** | `42ae4570d6a918a41d5df21017a5351ef2341e599087c0c07487de78979e9ebb` | 0 | **IMMUTABLE** |
| **Post-Sewing Blind Test** | `42ae4570d6a918a41d5df21017a5351ef2341e599087c0c07487de78979e9ebb` | 0 | **IMMUTABLE** |

**Conclusion: OpenSEO demonstrated true no-code arbitrary domain generalization across two completely disparate verticals with ZERO changes to generic core code.**
