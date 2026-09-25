# 30-Page Vehicle Camping Pilot Plan (Architecture & Entity Mapping)

> **Execution Directive**: PLAN ONLY. Do NOT mass-publish. All generated pilot articles must enter WordPress as `draft` and strictly satisfy the 9-point Quality Gate before human editorial review.

---

## 1. Executive Summary & Cluster Architecture

This pilot establishes an authoritative, calculation-grounded cluster targeting **Vehicle Camping & 12V Off-Grid Power/Refrigeration** across 5 high-volume utility platforms:
1. **Subaru Outback** (Gen 6: 2020–2025, Outback Wilderness)
2. **Subaru Forester** (Gen 5/6: 2019–2025, Forester Wilderness)
3. **Toyota RAV4** (Gen 5: 2019–2024, RAV4 Hybrid / Woodland)
4. **Honda CR-V** (Gen 6: 2023–2025)
5. **Ford Bronco** (6th Gen: 2021–2024, 4-Door Hardtop/Soft-top)

### Cluster Hierarchy Rules:
- **Pillar Pages (5)**: Comprehensive vehicle camping blueprints focusing on vehicle cargo dimensions, rear hatch clearances, OEM 12V aux socket limits, and power budget overviews.
- **Dedicated Fitment Guides (10)**: Strict 1:1 pairing between a verified vehicle platform and a specific high-efficiency 12V fridge (e.g., ICECO VL45, Dometic CFX3 45). Contains deterministic pass/fail fitment calculations, hatch clearance margins, and cord routing.
- **Power & Battery Section Guides (5)**: Electrical engineering breakdowns detailing inverter loss, duty cycle calculation, battery watt-hour sizing (Jackery, EcoFlow, LiFePO4), and alternator DC-DC charging safety.
- **Category Roundups (5)**: Intent-clustered comparison grids strictly ranked by dimensional clearance and measured amp-hour efficiency—NOT affiliate commission.
- **Sleeping Platform & Clearance Guides (5)**: Cargo floor angle, wheel well width constraints, and leveling requirements for car camping sleep setups.

---

## 2. 30-Page Content Matrix

| # | URL Slug | Primary Keyword | Intent | Hierarchy Type | Primary Entity | Secondary Entities | Monetization Policy | Inbound / Outbound Links |
|---|---|---|---|---|---|---|---|---|
| 01 | `/subaru-outback-camping-setup` | subaru outback camping setup | Informational / Blueprint | PILLAR_OVERVIEW | Subaru Outback (2020-2025) | ICECO VL45, EcoFlow River 2 Pro, Cargo Mat | Max 2 contextual links; zero aggressive popups | Links to #02, #03, #04, #05 |
| 02 | `/iceco-vl45-subaru-outback-fitment` | iceco vl45 subaru outback | Commercial Investigation | DEDICATED_FITMENT_GUIDE | ICECO VL45 Portable Fridge | Subaru Outback (2020-2025) | 1 direct manufacturer/merchant link on verified pass table | Outbound to #01 (Pillar), #03 (Power) |
| 03 | `/subaru-outback-fridge-power-setup` | subaru outback fridge power setup | Informational / Technical | SECTION_WITHIN_PILLAR | Subaru Outback 12V 10A Port | EcoFlow River 2, 12V Cigarette Socket | Link to tested 12V auxiliary cords & power station | Inbound from #01, #02; Outbound to #01 |
| 04 | `/best-fridge-for-subaru-outback` | best fridge for subaru outback | Commercial Investigation | CATEGORY_ROUNDUP | Subaru Outback Cargo Area | ICECO VL45, Dometic CFX3 35, BougeRV 30L | 1 link per verified-fit model in comparison matrix | Outbound to #02; Inbound from #01 |
| 05 | `/subaru-outback-car-camping-sleeping-platform` | subaru outback car camping sleeping | Informational / Guide | DEDICATED_FITMENT_GUIDE | Subaru Outback Cargo Bed | Luno Air Mattress, Exped Megamat Auto | Max 2 links to verified custom-fit sleeping pads | Outbound to #01 |
| 06 | `/subaru-forester-camping-setup` | subaru forester camping setup | Informational / Blueprint | PILLAR_OVERVIEW | Subaru Forester (2019-2025) | Dometic CFX3 45, Jackery 500, Forester Cargo | Max 2 contextual links | Links to #07, #08, #09, #10 |
| 07 | `/dometic-cfx3-45-subaru-forester-fitment` | dometic cfx3 45 subaru forester | Commercial Investigation | DEDICATED_FITMENT_GUIDE | Dometic CFX3 45 | Subaru Forester (2019-2025) | 1 direct verified merchant link | Outbound to #06, #08 |
| 08 | `/subaru-forester-12v-outlet-fridge-wiring` | subaru forester 12v outlet fridge | Informational / Technical | SECTION_WITHIN_PILLAR | Subaru Forester 12V 120W Port | Hardwire Kit, Aux Socket, 15A Fuse | Links to verified fuse-tap & low-voltage disconnects | Inbound from #06, #07; Outbound to #06 |
| 09 | `/best-fridge-for-subaru-forester` | best fridge for subaru forester | Commercial Investigation | CATEGORY_ROUNDUP | Subaru Forester Trunk Space | ICECO VL45, Dometic CFX3 45, Alpicool C20 | 1 link per verified fitment card | Outbound to #07; Inbound from #06 |
| 10 | `/subaru-forester-sleeping-platform-dimensions` | subaru forester sleeping platform | Informational / Dimensions | DEDICATED_FITMENT_GUIDE | Subaru Forester Rear Cargo | Cargo Leveling Block, Dual Sleeping Pad | Max 2 links to vehicle-tested pads | Outbound to #06 |
| 11 | `/toyota-rav4-camping-setup` | toyota rav4 camping setup | Informational / Blueprint | PILLAR_OVERVIEW | Toyota RAV4 (Gen 5 2019-2024) | EcoFlow Delta 2, ICECO GO20, RAV4 Hybrid | Max 2 contextual links | Links to #12, #13, #14, #15 |
| 12 | `/iceco-go20-toyota-rav4-fitment` | iceco go20 toyota rav4 | Commercial Investigation | DEDICATED_FITMENT_GUIDE | ICECO GO20 Dual Zone | Toyota RAV4 Gen 5 | 1 direct merchant link on fitment specs | Outbound to #11, #13 |
| 13 | `/toyota-rav4-hybrid-camping-ready-mode-power` | rav4 hybrid camping ready mode | Informational / Technical | SECTION_WITHIN_PILLAR | RAV4 Hybrid Traction Battery | 12V DC-DC Converter, Pure Sine Inverter | Link to pure sine 1000W inverter | Inbound from #11; Outbound to #11 |
| 14 | `/best-portable-fridge-for-toyota-rav4` | best portable fridge for toyota rav4 | Commercial Investigation | CATEGORY_ROUNDUP | Toyota RAV4 Trunk Compartment | ICECO VL45, Dometic CFX3 35, Anker EverFrost | 1 link per verified clearance product | Outbound to #12; Inbound from #11 |
| 15 | `/toyota-rav4-car-camping-level-floor-setup` | toyota rav4 car camping level floor | Informational / How-To | DEDICATED_FITMENT_GUIDE | Toyota RAV4 Rear Fold Flat | Folding Mattress, Leveling Riser | Max 2 links to floor leveling mats | Outbound to #11 |
| 16 | `/honda-crv-camping-setup` | honda crv camping setup | Informational / Blueprint | PILLAR_OVERVIEW | Honda CR-V (Gen 6 2023-2025) | Jackery 1000 Plus, BougeRV CR45 | Max 2 contextual links | Links to #17, #18, #19, #20 |
| 17 | `/bougerv-cr45-honda-crv-fitment` | bougerv cr45 honda crv | Commercial Investigation | DEDICATED_FITMENT_GUIDE | BougeRV CR45 Fridge | Honda CR-V (Gen 6) | 1 direct verified product link | Outbound to #16, #18 |
| 18 | `/honda-crv-12v-cargo-outlet-power-guide` | honda crv 12v cargo outlet power | Informational / Technical | SECTION_WITHIN_PILLAR | Honda CR-V 12V 180W Accessory Port | 12V Battery Isolator, Power Station | Links to 12V DC charging cord | Inbound from #16; Outbound to #16 |
| 19 | `/best-12v-fridge-for-honda-crv` | best 12v fridge for honda crv | Commercial Investigation | CATEGORY_ROUNDUP | Honda CR-V Cargo Bay | BougeRV CR45, Dometic CFX3 35, ICECO APL55 | 1 link per passing fridge model | Outbound to #17; Inbound from #16 |
| 20 | `/honda-crv-sleeping-in-car-camping-guide` | honda crv sleeping in car camping | Informational / Guide | DEDICATED_FITMENT_GUIDE | Honda CR-V Cargo Floor Step | Tailgate Tent, Custom Fit Foam Mattress | Max 2 links to sleeping gear | Outbound to #16 |
| 21 | `/ford-bronco-camping-setup` | ford bronco camping setup | Informational / Blueprint | PILLAR_OVERVIEW | Ford Bronco (4-Door 2021-2024) | ARB Elements 63Qt, Jackery Explorer 1000 | Max 2 contextual links | Links to #22, #23, #24, #25 |
| 22 | `/dometic-cfx3-55im-ford-bronco-fitment` | dometic cfx3 55im ford bronco | Commercial Investigation | DEDICATED_FITMENT_GUIDE | Dometic CFX3 55IM Fridge | Ford Bronco (4-Door) | 1 verified merchant link with slide tray note | Outbound to #21, #23 |
| 23 | `/ford-bronco-auxiliary-switches-fridge-wiring` | ford bronco aux switches fridge wiring | Informational / Technical | SECTION_WITHIN_PILLAR | Ford Bronco Upfitter Aux Switches | Relay Box, Anderson Powerpole Connector | Links to heavy gauge wiring harness & fuses | Inbound from #21; Outbound to #21 |
| 24 | `/best-offroad-fridge-for-ford-bronco` | best offroad fridge for ford bronco | Commercial Investigation | CATEGORY_ROUNDUP | Ford Bronco Cargo Slide Area | Dometic CFX3 55, ARB Classic II, ICECO VL60 | 1 link per rugged-rated fridge | Outbound to #22; Inbound from #21 |
| 25 | `/ford-bronco-rear-cargo-sleeping-platform` | ford bronco rear cargo sleeping | Informational / Dimensions | DEDICATED_FITMENT_GUIDE | Ford Bronco 4-Door Rear Incline | Rear Enclosure, Leveling Platform Kit | Max 2 links to Bronco-specific sleeping decks | Outbound to #21 |
| 26 | `/12v-car-camping-fridge-power-calculator` | 12v car fridge power consumption | Interactive Tool / Calculator | UTILITY_CALCULATOR | 12V Compressor Fridge Specs | LiFePO4 Battery, Ambient Temp Duty Cycle | Zero links inside tool UI; optional link below output | Inbound from all 5 Power Section Guides |
| 27 | `/portable-power-station-size-for-car-camping` | what size portable power station for camping | Informational / Calculation | CATEGORY_ROUNDUP | Portable Power Station Specs | EcoFlow, Jackery, Bluetti Wh Capacities | 1 link per Wh capacity tier (300Wh, 500Wh, 1000Wh) | Links to #26 (Calculator) |
| 28 | `/dc-to-dc-charger-vs-portable-power-station` | dc to dc charger vs portable power station | Informational / Comparison | TECHNICAL_COMPARISON | DC-DC Charger (Renogy/Redarc) | Portable Power Station (EcoFlow/Jackery) | 2 objective comparison links | Outbound to #03, #08, #13, #23 |
| 29 | `/car-camping-battery-drain-prevention-guide` | how to keep 12v fridge from killing car battery | Informational / Guide | SAFETY_GUIDE | Vehicle Starter Battery (Lead Acid/AGM) | Battery Low Voltage Cutoff (3-stage) | Links to digital voltmeter & 12V cutoff relay | Inbound from all 5 Pillar Guides |
| 30 | `/subaru-outback-wilderness-camping-modifications` | subaru outback wilderness camping setup | Commercial Investigation | DEDICATED_FITMENT_GUIDE | Subaru Outback Wilderness (2022-2025) | Geolandar AT Tires, Roof Rails (700lb limit) | Max 2 links to tested roof-top tent mounts | Inbound from #01; Outbound to #01 |

---

## 3. Strict Cannibalization & Intent Defense

To prevent keyword self-cannibalization between vehicle overviews, category roundups, and fitment guides:

1. **Exact Product Specificity Defense**:
   - Queries with brand + model (`iceco vl45 subaru outback`) are strictly routed to `DEDICATED_FITMENT_GUIDE` (#02).
   - Category roundup `#04` (`best fridge for subaru outback`) compares 4 models across distinct liter capacities and expressly delegates single-product deep dives to `#02` via canonical anchor text.
2. **Electrical Setup Scoping**:
   - Pillar overview `#01` references power in a 150-word summary table, pointing readers to `#03` (`subaru outback fridge power setup`) for complete circuit diagrams and duty cycle calculations.
3. **Trim Differentiation**:
   - `#30` explicitly scopes the **Outback Wilderness** (differing ground clearance, roof load dynamic 176 lb / static 700 lb, and altered cargo tie-downs) vs `#01` which covers standard Premium/Limited/Touring models.

---

## 4. Evidence Grounding & Fact Sourcing Rules

Prior to generating draft content for any page in this matrix, the pipeline mandates:
- **Vehicle Specs**: Extracted from OEM Owner's Manuals or certified press kits (cargo floor length with rear seats folded, hatch opening height, rear wheel well width, 12V aux port amperage rating).
- **Appliance Specs**: Extracted from manufacturer datasheets (exact exterior H x W x D with handles, compressor draw in Watts, cutoff voltage settings).
- **Calculations**: Executed deterministically through `CalculationEngine` with explicit temperature, duty cycle, and inverter efficiency uncertainty ranges (`ProvenanceFloat`).
- **Forbidden Phrases Filter**: Complete elimination of `"we tested"`, `"our hands-on review"`, or `"in our test car"`. All conclusions are framed strictly as:
  > *"Based on verified manufacturer dimensions (18.5" H) and measured cargo hatch opening (30.1" clearance), the ICECO VL45 provides 11.6 inches of overhead clearance."*

---

## 5. Monetization & Link Density Limits

- **Maximum Affiliate Links Per Article**: Strict ceiling of **3 links per 1,000 words** (link density < 0.003).
- **Mandatory Disclosure**: Direct statement preceding any affiliate link: *"We may earn a commission if you purchase through this link at no additional cost to you. Recommendations are derived strictly from physical fitment and electrical capacity matching."*
- **No Cloaked Redirect Spam**: All outbound commercial links must use clean, transparent rel tags (`rel="nofollow sponsored"`).
