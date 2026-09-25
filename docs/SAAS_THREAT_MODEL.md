# OpenSEO Multi-Tenant SaaS Threat Model (STRIDE)

## 1. Overview & System Scope

OpenSEO is an automated multi-tenant Data Authority engine and content orchestration platform. In a multi-tenant commercial deployment, multiple competing businesses, affiliate operators, and agencies run automated workflows across shared infrastructure. This threat model analyzes attack surfaces and documents security controls using the **STRIDE** methodology.

---

## 2. STRIDE Threat Analysis Matrix

| Threat Category | Attack Vector / Scenario | Pre-Hardening Risk | Architectural Mitigation | Status |
|---|---|---|---|---|
| **Spoofing** | Forged JWT tokens; token replay; unauthenticated request bypass. | **CRITICAL**: Missing auth headers defaulted to Admin ID 1. | Mandatory cryptographically signed JWT (`HS256`) with timing-safe `hmac.compare_digest`. Unique `jti` revocation tracking and token expiration validation. Zero fallback dev identities permitted. | **MITIGATED** |
| **Tampering** | Ciphertext tampering; API payload injection; formula modification. | **HIGH**: Hardcoded salt with reversible XOR cipher allowed ciphertext manipulation. | Authenticated symmetric encryption (**AES-256-GCM**) with 96-bit randomized nonces and GCM authentication tags. Tampered payloads fail authentication immediately with `CryptographicError`. | **MITIGATED** |
| **Repudiation** | Tenant claiming they did not alter site configuration or trigger mass crawling. | **MEDIUM**: Minimal audit metadata on mutations. | Immutable audit logs recording `request_id`, `user_id`, `tenant_id`, and ISO-8601 UTC timestamps on all site updates and lifecycle transitions. | **MITIGATED** |
| **Information Disclosure** | **Insecure Direct Object Reference (IDOR)**: Tenant B accessing Tenant A's sites, credentials, or niches; credentials leaking in exports or server errors. | **CRITICAL**: Endpoints accepted unvalidated `site_id` without verifying `site.tenant_id == user.tenant_id`. Plaintext leaked in exports. | Dual-layer tenant isolation: `verify_tenant_access()` checks at controller and model layers. Automatic credential masking (`••••••••`). Safe error shielding hiding internal stack traces. | **MITIGATED** |
| **Denial of Service (DoS)** | **Formula DoS**: Massive exponents ($2^{1000000}$), AST depth bombs, ReDoS; **Worker Exhaustion**: Unbounded thread spawning; API request floods. | **HIGH**: `SafeFormulaEngine` had no node limits or exponent caps; worker spawned unmanaged raw threads. | AST node limits ($\le 50$), expression length cap ($\le 1000$), exponent bounds ($\le 20$), magnitude clamp ($\le 10^{12}$). Bounded thread pool (`max_workers=5`), queue backpressure (`QueueFullError`), and sliding-window rate limiters. | **MITIGATED** |
| **Elevation of Privilege** | Normal VIEWER or EDITOR updating site lifecycle to ACTIVE or modifying credentials; tenant hopping. | **HIGH**: Endpoints relied on client-supplied `user_id`. | Server-side RBAC dependencies (`require_role(PermissionRole.ADMIN)`). Role and tenant extracted strictly from verified token claims. Cross-tenant context switching forbidden (403). | **MITIGATED** |

---

## 3. High-Priority Threat Scenarios & Mitigations

### 3.1. Cross-Tenant IDOR Attack
- **Threat**: An adversary authenticated as Tenant B issues `GET /api/v1/saas/sites/{site_id_a}/dashboard` or `POST /api/v1/saas/sites/{site_id_a}/credentials`.
- **Impact**: Exposure of competitor keywords, affiliate IDs, WordPress credentials, or private content strategies.
- **Control**: Every site lookup invokes `SaaSSiteManager.get_site(site_id, tenant_id=user.tenant_id)`. If the site's tenant does not match, the system raises HTTP 403 / 404 with zero internal metadata returned.
- **Test Evidence**: `tests/test_saas_idor_and_tenant_isolation.py` (100% pass).

### 3.2. Formula Engine Algorithmic DoS
- **Threat**: A malicious user submits a calculated attribute formula such as `"2 ** 1000000"` or `"(...(1 + 1)...)"` nested 500 times.
- **Impact**: CPU freeze or Python interpreter stack overflow halting all worker processes.
- **Control**:
  - `MAX_EXPRESSION_LENGTH = 1000`
  - `MAX_AST_NODES = 50`
  - `MAX_EXPONENT = 20`
  - `MAX_MAGNITUDE = 1e12`
  - Clean division-by-zero checks.
- **Test Evidence**: `tests/test_safe_formula_adversarial.py` (100% pass).

### 3.3. Unbounded Worker Concurrency Exhaustion
- **Threat**: Burst submission of 500 generation jobs leading to hundreds of concurrent threads and memory exhaustion.
- **Impact**: Host OOM crash and dropped HTTP connections.
- **Control**: `ProductionJobEngine` bounds concurrency via `ThreadPoolExecutor(max_workers=5)`. Queue capacity limits apply backpressure (`QueueFullError`). Idempotency keys prevent duplicate processing.
- **Test Evidence**: `tests/test_background_jobs_and_idempotency.py` (100% pass).

### 3.4. Runaway AI Cost & Billing Spike
- **Threat**: LLM agent enters an infinite tool-calling loop or mass-processes SERP queries, racking up massive third-party API bills.
- **Impact**: Unbudgeted thousands of dollars in LLM/SERP costs.
- **Control**:
  - `TenantQuotaManager`: Enforces monthly token and query quotas per plan tier.
  - `CostGuardrails`: Enforces daily and monthly monetary spend limits ($5 starter, $25 growth, $100 agency daily).
  - `AILoopBreaker`: Hard limit of 10 LLM invocations and 8 tool iterations per job execution.
- **Test Evidence**: `tests/test_rate_limiting_and_cost_guardrails.py` (100% pass).

---

## 4. Residual Risks & Operational Guidance
1. **Host-Level Database Deployment**: Local development operates on SQLite; real PostgreSQL is required for multi-pod production horizontal scaling.
2. **Secrets Rotation Cadence**: Master encryption keys should be rotated every 90 days using `EncryptedCredentialStore.rotate_all_credentials()`.
3. **Third-Party Provider Outages**: Transient 429/5xx errors are absorbed by exponential backoff with jitter and routed to Dead Letter Queue (DLQ) if persistent.
