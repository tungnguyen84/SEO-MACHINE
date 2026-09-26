# First-Time User Journey Audit: No-Code Authority Site Creation
**Niche: Home Dehumidifiers (US Market)**
*Date: 2026-09-26 | Persona: Non-Technical Homeowner / Entrepreneur*

---

## 1. Journey Overview & User Flow

The first-time user journey in OpenSEO is designed around a single guiding principle: **"Describe your vision in plain English; OpenSEO handles the engineering, science, and search modeling."**

```mermaid
flowchart LR
    S1["1. Site Wizard\n(Name, Domain, Market)"] --> S2["2. Vision Input\n(Plain English Prompt)"]
    S2 --> S3["3. AI Design & Critique\n(Interactive Proposal)"]
    S3 --> S4["4. Interactive Tuning\n(One-Click Approvals)"]
    S4 --> S5["5. Strategy & Planning\n(30 Topic Hubs)"]
    S5 --> S6["6. Asynchronous Build\n(Friendly Live Status)"]
    S6 --> S7["7. Editorial Review\n(Claim Inspector & Sign-off)"]
```

---

## 2. Step-by-Step Screen Audit

### Screen 1: Site Onboarding Wizard
- **URL/View**: `/app/sites/new`
- **Fields Presented**:
  - Site Name: `"DehumidifierGuide US"`
  - Target Market: `"United States (en-US)"`
  - Domain: `"dehumidifierguide.com"`
  - Business Model: `"Affiliate / Editorial Reviews"`
- **Total Clicks**: 3 clicks (Enter details, select country/currency, click "Next").
- **Cognitive Load**: Minimal. Matches familiar SaaS setup wizards (Shopify, Ghost).

### Screen 2: Niche Vision Prompt
- **URL/View**: `/app/sites/{id}/niche-designer`
- **Prompt Entered**:
  > *"I want to build a US website helping homeowners choose dehumidifiers based on room size, humidity, basement conditions, energy use, drainage options and running cost. The site may monetize with affiliate links."*
- **User Actions**: Click "Generate Niche Blueprint".
- **Elapsed Time**: 1.8 seconds.

### Screen 3: Blueprint Review & Critic Suggestions
- **URL/View**: `/app/sites/{id}/niche-blueprint`
- **What the User Sees**:
  - Visual cards representing key concepts: **Dehumidifiers**, **Rooms**, **Basements**.
  - Attribute pills: Capacity (Pints/Day), Sizing Area, Energy Factor (IEF), Built-in Pump, Sound Level, Operating Temp.
  - Interactive "Critic Card": *"Tip: We've calibrated pint capacities to the 2019 DOE testing standards (65°F/60% RH) rather than legacy 2012 standards to prevent customer confusion."*
  - Interactive Formula Simulator: Pre-filled calculation showing annual running costs with an editable electricity price slider (\$0.16/kWh).
- **User Actions**: One click to "Approve Blueprint & Continue".

### Screen 4: Content Strategy & 30-Page Plan
- **URL/View**: `/app/sites/{id}/content-planner`
- **What the User Sees**:
  - Organized topical cluster tree:
    - *Room Sizing Cluster* (Small rooms, Large basements, Crawlspaces).
    - *Features & Drainage* (Internal pumps vs gravity hoses, low-temperature auto-defrost).
    - *Efficiency & Costs* (Annual electricity calculators, Energy Star savings).
    - *Head-to-Head Comparisons* (Frigidaire vs Midea 50-pint shootouts).
  - Cannibalization badge: *"3 overlapping topics automatically consolidated to preserve Google rankings."*
- **User Actions**: Select initial 5 drafts to generate; click "Generate Drafts".

### Screen 5: Background Processing with Friendly Progress
- **URL/View**: `/app/sites/{id}/activity`
- **What the User Sees**:
  - Friendly stage indicators: `Waiting` ➔ `Researching` ➔ `Analyzing` ➔ `Writing` ➔ `Checking` ➔ `Ready for Review`.
  - Non-technical progress updates: *"Verifying manufacturer specifications for Frigidaire 50-Pint..."*, *"Checking DOE energy star ratings..."*
- **Resilience**: If the user closes their browser or their connection drops, durable server workers continue processing. Reopening the app immediately resumes live state.

### Screen 6: Editorial Review & Claim Inspector
- **URL/View**: `/app/sites/{id}/editorial/{article_id}`
- **What the User Sees**:
  - Full article preview formatted cleanly in rich typography.
  - **Claim Inspector Sidebar**:
    - 🟢 **Verified Fact** (e.g. 50 pint/day capacity confirmed by DOE database).
    - 🔵 **Calculated** (e.g. \$147.17 annual electricity cost based on 420W @ \$0.16/kWh).
    - 🟣 **Modelled** (e.g. Suitability score 98% for damp 1,200 sq ft basements).
    - 🟡 **Assumption** (e.g. Average US utility baseline).
  - One-click editorial action buttons: **Preview**, **Edit In-Line**, **Request Rewrite**, **Approve**, **Reject**.

---

## 3. Technical Concepts Hidden from the User

To ensure complete accessibility for non-technical creators, the OpenSEO interface strictly conceals all internal engineering abstractions:

| Internal Engine Concept | Concealed Engineering Detail | User-Facing Representation |
| :--- | :--- | :--- |
| **AST Whitelist Evaluation** | `ast.parse()`, safe operator node traversal, visitor patterns | *"Tested Calculation: Annual Running Cost ($294.34/yr)"* |
| **PostgreSQL & SQLAlchemy ORM** | Foreign key constraints, Alembic migrations, pool recycling | *"Your project settings have been saved"* |
| **Durable Jobs State Machine** | Leases, worker heartbeats, zombie recovery, exponential backoffs | *"Checking and polishing your draft..."* |
| **Cannibalization Matrices** | Cosine semantic similarity, SERP cluster vector distances | *"We combined 2 similar topics into 1 comprehensive guide to avoid keyword conflict."* |
| **Evidence Provenance Chains** | Hash chains, citation pointers, deterministic fact graphs | *"Verified Fact (Source: DOE Energy Star Database)"* |
| **Rate Limiters & Cost Budgets** | Token sliding window buckets, redis rate throttles | *"Job is actively researching your product specifications"* |

---

## 4. Friction Points & UX Simplifications

### Friction 1: Multi-Attribute Sizing Complexity
- *The Problem*: Dehumidifier sizing depends on both room area (sq ft) and dampness level (moderately damp, very damp, wet, extremely wet). A novice user might not know how to define multi-variable logic.
- *OpenSEO Solution*: The AI Designer auto-seeded the official Association of Home Appliance Manufacturers (AHAM) / DOE standard room matrix without requiring the user to write conditional branches.

### Friction 2: Ambiguous Technical Jargon
- *The Problem*: Terms like *IEF (Integrated Energy Factor)* or *DOE 2019 vs 2012 testing conditions* confuse average users.
- *OpenSEO Solution*: The AI Critic proactively generated explanatory tooltips and plain-language summaries (e.g., *"Energy Factor measures how many liters of water are removed per kilowatt-hour of power"*).

### Friction 3: Confidence in Generated Technical Claims
- *The Problem*: Affiliate site owners dread publishing false specifications (e.g., wrong pint capacity or misleading energy claims) that erode consumer trust.
- *OpenSEO Solution*: The **Claim Inspector** displays clickable verification tags next to every number and rating, allowing creators to verify facts in seconds with zero manual googling.

---

## 5. First-Time Journey Metrics
- **Total Screens Navigated**: 6 screens.
- **Total Decision Points for User**: 4 (Review Niche, Approve Strategy, Choose Drafts, Approve Article).
- **Time from Initial Vision to First Review-Ready Article**: Under 4 minutes.
- **User Code / Scripting Required**: Exactly 0 lines.
