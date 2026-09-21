# Confidential Computing Roadmap
## AMD SEV-SNP and Intel SGX Implementation Strategy with ROI Analysis

**Date:** October 14, 2025
**Purpose:** Determine when, how, and why to implement confidential computing for compute marketplace

---

## Executive Summary

Confidential computing (AMD SEV-SNP for VMs, Intel SGX for applications, H100 GPU TEE for GPU workloads) represents a **$10B+ market unlock** for enterprise customers who cannot use untrusted infrastructure without memory encryption. However, it requires **$500K-1M investment** and adds **2-10% performance overhead**.

**Key Recommendation:** Do NOT implement for MVP. Add in Phase 2 (months 7-18) when first enterprise customer demands it. The technology is mature enough (2025), but the customer demand and willingness to pay premium pricing must justify the investment.

**Break-even Analysis:** Requires $10M+/year revenue from confidential computing to justify $1M implementation cost + ongoing operational overhead.

---

## Technology Options Comparison

### AMD SEV-SNP (Secure Encrypted Virtualization - Secure Nested Paging)

**Architecture:**
- VM-level memory encryption
- Each VM has encrypted memory (invisible to hypervisor/provider)
- Hardware-based attestation via AMD Secure Processor
- Protects against malicious infrastructure owner

**Performance:**
- Overhead: 2-10% (typically 5% for CPU-bound workloads)
- Memory encryption: AES-128
- Negligible impact for compute-heavy jobs
- Higher impact for memory-bandwidth intensive workloads

**Hardware Requirements:**
- AMD EPYC Milan (3rd Gen) or newer processors
- Motherboard with SEV-SNP support
- DDR4 RAM (encrypted in-memory)
- Cost: ~$8K-15K per server (vs $5K-8K standard)

**Software Stack:**
- QEMU 6.2+ with SEV-SNP support
- Linux kernel 5.19+ (host and guest)
- OVMF firmware (UEFI for VMs)
- Attestation service (Intel Trust Authority or custom)

**Use Cases:**
- Healthcare data processing (HIPAA compliance)
- Financial transactions (PCI-DSS)
- Proprietary ML model training (IP protection)
- Government workloads (classified data)
- Multi-tenant environments with untrusted providers

**Maturity (2025):** PRODUCTION-READY
- First release: 2020 (SEV), 2021 (SEV-SNP)
- Azure confidential VMs: General availability 2023
- Linux kernel support: Stable since 5.19 (2022)
- 5+ years of production experience

---

### Intel SGX (Software Guard Extensions)

**Architecture:**
- Application-level enclaves (not VM-level)
- Encrypted memory regions within process
- Protected from OS, hypervisor, other applications
- Smaller trust boundary than SEV-SNP

**Performance:**
- Overhead: 5-50% (highly workload-dependent)
- Enclave entry/exit: 10,000+ CPU cycles
- Best for: Infrequent enclave calls, sensitive data operations
- Worst for: Frequent enclave transitions

**Hardware Requirements:**
- Intel CPUs with SGX support (Xeon E-series, Ice Lake+)
- Enclave Page Cache (EPC) size: 128MB (older) to 256MB+ (newer)
- Cost: Similar to AMD EPYC servers

**Software Stack:**
- Intel SGX SDK
- Linux SGX driver
- DCAP (Data Center Attestation Primitives)
- Application code modifications required (unlike SEV-SNP)

**Use Cases:**
- Key management services
- Secure enclaves for sensitive operations
- Confidential smart contracts
- Certificate authorities
- Limited-size confidential data (EPC constraints)

**Limitations:**
- Enclave size limits (128-256MB) - problematic for ML models
- Application must be rewritten for SGX
- Side-channel vulnerabilities discovered (Spectre, Foreshadow)
- More complex than SEV-SNP for full workload protection

**Maturity (2025):** MATURE but DECLINING
- First release: 2015
- Many side-channel vulnerabilities discovered
- Intel shifting focus to TDX (Trust Domain Extensions)
- Azure deprecating SGX in favor of TDX/SEV-SNP

**Recommendation:** Prefer AMD SEV-SNP over Intel SGX for compute marketplace (VM-level simpler than application-level)

---

### Intel TDX (Trust Domain Extensions)

**Architecture:**
- VM-level encryption (like SEV-SNP)
- Competes directly with AMD SEV-SNP
- Protects VMs from hypervisor
- More recent than SEV-SNP

**Performance:**
- Overhead: Similar to SEV-SNP (2-10%)
- Hardware-based encryption
- Attestation via Intel Attestation Service

**Hardware Requirements:**
- Intel Sapphire Rapids (4th Gen Xeon) or newer
- Limited hardware availability (2023+)
- Cost: Premium pricing for latest Intel servers

**Maturity (2025):** EMERGING (not production-ready)
- First release: 2023 (limited availability)
- Azure preview: 2024
- Less mature than SEV-SNP (fewer production deployments)
- Growing ecosystem support

**Recommendation:** Monitor but don't implement yet. SEV-SNP more mature and wider hardware availability.

---

### NVIDIA H100 GPU Confidential Computing

**Architecture:**
- Encrypted bounce buffer between CPU and GPU
- Protects GPU memory from provider inspection
- Works with AMD SEV-SNP or Intel TDX (CPU encryption)
- Double encryption: CPU memory + GPU transfers

**Performance:**
- Overhead: 5-15% (encryption of CPU↔GPU transfers)
- Minimal impact on pure GPU compute
- Higher impact on frequent CPU-GPU transfers

**Hardware Requirements:**
- NVIDIA H100 GPUs (~$30K each)
- AMD EPYC (SEV-SNP) or Intel Xeon (TDX) servers
- PCIe 5.0 for optimal performance

**Use Cases:**
- Healthcare ML (encrypted medical imaging)
- Financial ML (encrypted transaction data)
- Proprietary model training (protect IP)
- Federated learning (confidential data stays encrypted)

**Maturity (2025):** PRODUCTION-READY
- Announced: 2022 (with H100 launch)
- General availability: 2023
- Azure confidential GPU VMs: 2024
- 2+ years production experience

**Recommendation:** Phase 3 feature for premium enterprise customers (hardware cost $30K+ per GPU)

---

## When to Implement Confidential Computing?

### Decision Framework

**Do NOT implement if:**
- ❌ No customer demand (no one asking for it)
- ❌ Customers not willing to pay 2-3x premium
- ❌ MVP stage (months 1-6) - too complex
- ❌ Budget constraints (<$500K available)
- ❌ Team lacks specialized expertise

**Consider implementing if:**
- ✅ First enterprise customer DEMANDS it (contract contingent)
- ✅ Regulated industry target (healthcare, finance, government)
- ✅ Competitor offers it (competitive pressure)
- ✅ $10M+ revenue opportunity from confidential computing
- ✅ Phase 2 or later (months 7-18+)

**Definitely implement if:**
- ✅ Multiple enterprise customers requesting
- ✅ Compliance certification required (HIPAA, PCI-DSS, FedRAMP)
- ✅ Clear path to $50M+ revenue from enterprise segment
- ✅ Competitive differentiation (Vast.ai, Golem cannot offer)

---

## Phased Implementation Roadmap

### Phase 1 (MVP - Months 1-6): NO Confidential Computing

**Rationale:**
- Too complex for MVP
- No customer demand yet
- $500K+ investment not justified
- Team needs to focus on core marketplace functionality

**Risk Accepted:**
- Provider can inspect workload memory
- Not suitable for regulated industries
- Enterprise customers will wait

**Alternative:**
- Position as "roadmap item"
- Gauge customer interest
- Design architecture with future SEV-SNP in mind

---

### Phase 2 (Growth - Months 7-18): Conditional Implementation

**Trigger Conditions (ANY of these):**
1. First enterprise customer demands confidential computing (contract $1M+/year)
2. Regulated industry customer (healthcare, finance) requires HIPAA/PCI-DSS
3. Competitive pressure (competitor launches confidential computing)
4. Clear pipeline of $10M+ enterprise revenue contingent on feature

**Implementation Timeline:**
- **Month 1-2:** Hardware procurement (AMD EPYC servers, H100 GPUs)
- **Month 3-6:** Software integration (QEMU, attestation service, KMS)
- **Month 7-9:** Beta testing with first enterprise customer
- **Month 10-12:** General availability, compliance certification

**Investment Required:**
- Hardware: $300K (20x AMD EPYC servers @ $15K each)
- Engineering: $400K (5 engineers × 4 months)
- Compliance: $150K (HIPAA audit, SOC 2 Type II)
- **Total:** $850K

**Revenue Target:**
- First year: $5M from confidential computing (break-even in ~2 years)
- Long-term: $20M+/year (justify investment + ongoing costs)

**Pricing Strategy:**
- Confidential VMs: 2-3x standard pricing
- H100 confidential GPU: 4-5x standard GPU pricing
- Positioning: Enterprise premium tier

---

### Phase 3 (Scale - Months 19+): Standard Enterprise Offering

**Expansion:**
- Deploy SEV-SNP in all regions
- Add H100 confidential GPUs to all GPU clusters
- Compliance certifications: HIPAA, PCI-DSS, FedRAMP
- Marketing: "Enterprise-grade confidential computing"

**Investment:**
- Hardware: $1M+ (fleet-wide deployment)
- Compliance: $300K (multiple certifications)
- Engineering: $200K (ongoing optimization)
- **Total:** $1.5M

**Revenue Target:**
- $50M+/year from enterprise segment
- 20-30% of total GMV from confidential workloads
- 3-5x higher margins vs standard workloads

**Market Position:**
- Only P2P marketplace with confidential computing
- Enterprise differentiation vs Vast.ai, Golem, Akash
- Unlock regulated industries (healthcare, finance, government)

---

## ROI Analysis

### Cost Breakdown (First 3 Years)

**Year 1 (Phase 2 Pilot):**
- Hardware: $300K (initial 20 servers)
- Engineering: $400K (implementation)
- Compliance: $150K (first certification)
- Operational: $50K (attestation service, support)
- **Total:** $900K

**Year 2 (Phase 2 Expansion):**
- Hardware: $400K (40 more servers)
- Engineering: $200K (optimization, maintenance)
- Compliance: $100K (additional certifications)
- Operational: $150K (increased usage)
- **Total:** $850K

**Year 3 (Phase 3 Standard Offering):**
- Hardware: $500K (100 more servers, H100 GPUs)
- Engineering: $150K (maintenance)
- Compliance: $50K (annual audits)
- Operational: $300K (scale operations)
- **Total:** $1M

**Cumulative 3-Year Cost:** $2.75M

---

### Revenue Projections (Conservative)

**Year 1 (Pilot):**
- Customers: 5 enterprise customers
- Average contract: $1M/year
- Confidential computing revenue: $5M
- Gross margin: 60% (premium pricing)
- Gross profit: $3M
- **Net:** $3M - $900K = **+$2.1M**

**Year 2 (Expansion):**
- Customers: 20 enterprise customers
- Average contract: $1.2M/year
- Confidential computing revenue: $24M
- Gross margin: 60%
- Gross profit: $14.4M
- **Net:** $14.4M - $850K = **+$13.55M**

**Year 3 (Standard Offering):**
- Customers: 50 enterprise customers
- Average contract: $1.5M/year
- Confidential computing revenue: $75M
- Gross margin: 60%
- Gross profit: $45M
- **Net:** $45M - $1M = **+$44M**

**Cumulative 3-Year Profit:** $59.65M (revenue) - $2.75M (cost) = **+$56.9M**

**ROI:** ($56.9M / $2.75M - 1) × 100% = **1,969% over 3 years**

---

### Break-Even Analysis

**Question:** How much revenue needed to justify $900K first-year investment?

**Assumptions:**
- Gross margin: 60% (premium pricing, 2-3x standard)
- Cost: $900K (first year)

**Break-even revenue:**
$900K / 0.60 = **$1.5M first year**

**Required customers:**
- At $1M/year average: **2 enterprise customers**
- At $500K/year average: **3 enterprise customers**

**Conclusion:** Very achievable. If even ONE enterprise customer commits $1.5M+/year contract contingent on confidential computing, the investment is justified.

---

### Sensitivity Analysis

**Scenario 1: Pessimistic (50% of projections)**
- Year 1: 2-3 customers, $2.5M revenue
- Year 2: 10 customers, $12M revenue
- Year 3: 25 customers, $37.5M revenue
- **3-Year Profit:** $28.5M (still excellent ROI)

**Scenario 2: Optimistic (150% of projections)**
- Year 1: 7-8 customers, $7.5M revenue
- Year 2: 30 customers, $36M revenue
- Year 3: 75 customers, $112.5M revenue
- **3-Year Profit:** $85M+ (exceptional ROI)

**Scenario 3: Delayed Adoption (Year 2 start)**
- Year 1: $0 (no implementation)
- Year 2: $5M revenue (delayed start)
- Year 3: $24M revenue (growth)
- **3-Year Profit:** $26.25M (still positive, but missed Year 1 opportunity)

**Key Insight:** Even pessimistic scenarios show positive ROI. The risk is NOT financial loss, but rather OPPORTUNITY COST of not capturing enterprise market.

---

## Enterprise Use Cases

### 1. Healthcare: HIPAA-Compliant ML Training

**Customer:** Hospital network training diagnostic AI models
**Data:** Medical imaging (MRI, CT scans, X-rays) - PHI (Protected Health Information)
**Regulatory:** HIPAA requires encryption at-rest, in-transit, AND in-use
**Solution:** AMD SEV-SNP VMs + H100 confidential GPUs

**Workflow:**
1. Hospital uploads encrypted medical images to platform S3
2. Platform provisions SEV-SNP VM with H100 GPU
3. VM attests integrity to hospital (remote attestation)
4. Hospital releases decryption keys to verified VM
5. ML training proceeds with encrypted memory
6. Results encrypted and returned to hospital
7. VM memory wiped, GPU reset

**Value Proposition:**
- Hospital cannot use standard cloud (AWS/Azure) without BAA (Business Associate Agreement)
- P2P marketplace with confidential computing enables HIPAA compliance
- 70-90% cost savings vs AWS confidential VMs

**Contract Size:** $2M-5M/year (multiple hospitals in network)

---

### 2. Finance: PCI-DSS Fraud Detection

**Customer:** Fintech company training fraud detection models
**Data:** Credit card transactions (PCI-DSS Cardholder Data Environment)
**Regulatory:** PCI-DSS Level 1 requires strict data protection
**Solution:** AMD SEV-SNP VMs with attestation

**Workflow:**
1. Fintech provisions SEV-SNP VM for fraud detection training
2. Platform provides attestation report (prove VM integrity)
3. Fintech's HSM (Hardware Security Module) releases keys to attested VM
4. Training proceeds with encrypted transaction data
5. Model exported in encrypted form
6. VM destroyed, memory wiped

**Value Proposition:**
- PCI-DSS compliance without building internal infrastructure
- Cost-effective confidential computing vs hyperscalers
- Flexibility to scale training jobs up/down

**Contract Size:** $1M-3M/year

---

### 3. Pharma: Proprietary Drug Discovery Models

**Customer:** Pharmaceutical company training molecular models
**Data:** Proprietary chemical compounds, drug candidates (TRADE SECRET)
**Risk:** IP theft (competitors, industrial espionage)
**Solution:** AMD SEV-SNP VMs (no GPU required, CPU-only molecular dynamics)

**Workflow:**
1. Pharma company provisions SEV-SNP VMs
2. Remote attestation verifies platform integrity
3. Encrypted molecular simulation data uploaded
4. Simulation runs with encrypted memory
5. Results encrypted, exported
6. Provider CANNOT access simulation data (hardware-enforced)

**Value Proposition:**
- IP protection (trade secrets worth billions)
- Cannot use public cloud without confidential computing
- Cost savings vs building internal HPC cluster

**Contract Size:** $3M-10M/year (large pharma companies)

---

### 4. Government: Classified Workloads (FedRAMP)

**Customer:** US Department of Defense, Intelligence agencies
**Data:** Classified information (SECRET, TOP SECRET)
**Regulatory:** FedRAMP High, IL-5 (Impact Level 5) for classified
**Solution:** AMD SEV-SNP + H100 confidential GPU + FedRAMP compliance

**Workflow:**
1. Government agency provisions SEV-SNP VMs in FedRAMP-authorized region
2. Multi-party attestation (DoD + Platform + AMD)
3. Classified data processed in encrypted memory
4. Results exported through secure gateway
5. Continuous monitoring, audit logs

**Value Proposition:**
- FedRAMP High certification enables government contracts
- Confidential computing required for classified workloads
- $10B+ government cloud market (TAM)

**Contract Size:** $10M-100M/year (government contracts are massive)

**Note:** FedRAMP requires 18-36 months compliance process, $1M+ investment. Only pursue if serious about government market.

---

## Attestation Architecture

### Remote Attestation Flow

**Purpose:** Prove to user that their workload is running in genuine SEV-SNP VM, not fake/compromised environment

**Actors:**
1. **User:** Wants to run confidential workload
2. **Platform:** Compute marketplace
3. **AMD Secure Processor (ASP):** Hardware root of trust in EPYC CPU
4. **Attestation Service:** Verifies attestation reports (Intel Trust Authority or self-hosted)

**Flow:**
```
1. User submits job → Platform
2. Platform provisions SEV-SNP VM
3. Platform requests attestation report → AMD ASP
4. AMD ASP generates signed report (includes VM measurement, platform TCB)
5. AMD ASP returns report → Platform
6. Platform forwards report → User
7. User verifies report signature → Attestation Service
8. Attestation Service validates:
   - AMD signature (authentic hardware)
   - Platform certificates (authorized AMD EPYC)
   - TCB version (security patch level)
   - VM measurement (correct kernel, firmware)
9. If valid: Attestation Service issues JWT token → User
10. User validates JWT against policy (e.g., "TCB >= v1.51")
11. If pass: User releases encryption keys → VM
12. VM decrypts data, runs computation
13. Results encrypted, returned to user
```

**Security Properties:**
- User can verify workload runs on genuine AMD SEV-SNP hardware
- User can verify platform hasn't tampered with VM
- User can verify VM measurement (kernel, firmware integrity)
- User controls when to release secrets (after attestation passes)

**Implementation Options:**

**Option 1: Intel Trust Authority (Managed Service)**
- **Pros:** Fully managed, no infrastructure
- **Cons:** $0.10-0.50 per attestation (cost at scale)
- **Best for:** Phase 2 pilot (low volume)

**Option 2: Self-Hosted Attestation Service**
- **Pros:** No per-attestation cost, full control
- **Cons:** Must maintain AMD certificate chains, infrastructure
- **Best for:** Phase 3 scale (high volume)

**Recommendation:** Start with Intel Trust Authority, migrate to self-hosted when >10,000 attestations/month

---

## Key Management System (KMS)

### Customer-Managed Keys (CMK)

**Requirement:** Enterprise customers demand control over encryption keys (trust no one, not even platform)

**Architecture:**
```
User's KMS (AWS KMS, Azure Key Vault, HashiCorp Vault)
    ↓
Platform's KMS proxy (does NOT store keys)
    ↓
SEV-SNP VM (keys released ONLY after attestation)
```

**Workflow:**
1. User generates encryption keys in their KMS (e.g., AWS KMS)
2. User configures policy: "Release keys ONLY to VMs with attestation report matching X"
3. VM requests keys from User's KMS
4. User's KMS demands attestation report
5. Platform provides attestation report (from AMD ASP)
6. User's KMS verifies attestation
7. If valid: User's KMS releases keys directly to VM (encrypted transport)
8. VM decrypts data
9. **At no point does platform have access to decryption keys**

**Implementation:**
- Platform provides KMS integration SDKs (AWS, Azure, GCP, HashiCorp)
- User brings their own keys (BYOK)
- Platform never stores keys (zero-knowledge encryption)

---

## Compliance Certifications

### HIPAA (Health Insurance Portability and Accountability Act)

**Requirements:**
- Encryption at-rest, in-transit, in-use
- Access controls (PHI only accessible to authorized users)
- Audit logs (who accessed what, when)
- Business Associate Agreement (BAA) with healthcare customers

**Timeline:** 12-18 months
**Cost:** $150K (audit, remediation, legal)

**Confidential Computing Alignment:**
- SEV-SNP provides in-use encryption (solves HIPAA's hardest requirement)
- Attestation provides audit trail (prove workload integrity)
- Key management (user-controlled, never exposed to platform)

---

### PCI-DSS (Payment Card Industry Data Security Standard)

**Requirements:**
- Cardholder data encrypted
- Network segmentation (isolate payment systems)
- Access controls (principle of least privilege)
- Logging and monitoring

**Timeline:** 18-24 months
**Cost:** $200K (QSA audit, remediation)

**Level:** Likely Level 1 (>6M transactions/year) - most stringent

**Confidential Computing Alignment:**
- SEV-SNP encrypts cardholder data in memory
- Kata Containers provide network isolation
- Attestation provides cryptographic proof of isolation

---

### FedRAMP (Federal Risk and Authorization Management Program)

**Requirements:**
- NIST 800-53 controls (>900 controls for FedRAMP High)
- Continuous monitoring
- Incident response
- Physical security
- Personnel security clearances

**Timeline:** 24-36 months (FedRAMP High)
**Cost:** $1M-2M (extremely rigorous)

**Levels:**
- **FedRAMP Low:** Non-sensitive government data
- **FedRAMP Moderate:** CUI (Controlled Unclassified Information)
- **FedRAMP High:** Classified up to SECRET

**Recommendation:** Only pursue if serious about government contracts (long timeline, high cost)

---

## Competitive Differentiation

### Competitors WITHOUT Confidential Computing

**Vast.ai:**
- No confidential computing
- Provider can inspect memory
- Not suitable for regulated industries

**Golem Network:**
- Redundancy-based verification (expensive)
- No memory encryption
- Not HIPAA/PCI-DSS compliant

**Akash Network:**
- Standard Kubernetes (no confidential VMs)
- No attestation
- Not enterprise-ready

### Competitors WITH Confidential Computing

**AWS, Azure, GCP:**
- All offer SEV-SNP/TDX confidential VMs
- 3-5x MORE EXPENSIVE than P2P marketplace
- Lock-in (proprietary APIs)

**Our Advantage:**
- **70-90% cost savings** vs hyperscalers
- **P2P marketplace flexibility** (choose providers, regions, hardware)
- **Confidential computing without lock-in** (standard VM, no proprietary APIs)

---

## Risk Mitigation

### Technical Risks

**Risk 1: SEV-SNP Vulnerabilities Discovered**
- **Likelihood:** MEDIUM (new vulnerabilities found periodically)
- **Impact:** HIGH (customer trust, compliance)
- **Mitigation:**
  - Stay current with AMD security advisories
  - Rapid patching process (TCB updates)
  - Customer communication (transparency)
  - Consider migration to TDX if SEV-SNP fundamentally broken

**Risk 2: Performance Overhead Higher Than Expected**
- **Likelihood:** LOW (well-characterized at 2-10%)
- **Impact:** MEDIUM (customer satisfaction)
- **Mitigation:**
  - Extensive benchmarking before GA
  - Clear SLA expectations (95% of native performance)
  - Option to disable SEV-SNP if performance unacceptable

**Risk 3: Hardware Availability Constraints**
- **Likelihood:** MEDIUM (AMD EPYC shortages possible)
- **Impact:** MEDIUM (delayed deployment)
- **Mitigation:**
  - Pre-order hardware (long lead times)
  - Diversify to Intel TDX (dual-source)
  - Gradual rollout (not big-bang)

### Market Risks

**Risk 1: Customer Demand Lower Than Projected**
- **Likelihood:** LOW (clear enterprise need)
- **Impact:** HIGH (ROI not realized)
- **Mitigation:**
  - Pilot with first customer BEFORE full deployment
  - Contract commitment ($1M+) before hardware purchase
  - Gradual expansion based on demand

**Risk 2: Competitors Launch Confidential Computing First**
- **Likelihood:** MEDIUM (Vast.ai could add SEV-SNP)
- **Impact:** MEDIUM (lost first-mover advantage)
- **Mitigation:**
  - Monitor competitors closely
  - Accelerate timeline if competitor moves
  - Differentiate on price (70-90% cheaper than AWS)

**Risk 3: Compliance Certification Delays**
- **Likelihood:** HIGH (HIPAA/PCI-DSS/FedRAMP are slow)
- **Impact:** MEDIUM (delayed revenue)
- **Mitigation:**
  - Start compliance early (before GA)
  - Hire compliance consultants (expensive but faster)
  - Interim: Serve non-regulated customers first

---

## Conclusion

**Key Decisions:**

1. **Do NOT implement confidential computing for MVP**
   - Too complex, too expensive, no demand yet
   - Risk accepted: Enterprise customers will wait

2. **Implement in Phase 2 (months 7-18) when:**
   - First enterprise customer commits $1M+/year contract
   - OR regulated industry customer requires HIPAA/PCI-DSS
   - OR competitive pressure (Vast.ai launches confidential computing)

3. **Technology choice: AMD SEV-SNP (not Intel SGX)**
   - VM-level encryption (simpler than app-level)
   - Mature (2020 release, 5+ years production)
   - Wider hardware availability vs Intel TDX

4. **Investment: $900K first year, $2.75M over 3 years**
   - Break-even: $1.5M revenue (2-3 enterprise customers)
   - Conservative projection: $59.65M profit over 3 years
   - ROI: 1,969% (exceptional)

5. **Pricing: 2-3x premium vs standard VMs**
   - Justified by security, compliance, IP protection
   - Still 70-90% cheaper than AWS confidential VMs

6. **Compliance: HIPAA first, then PCI-DSS, FedRAMP later**
   - HIPAA: 12-18 months, $150K (healthcare market)
   - PCI-DSS: 18-24 months, $200K (fintech market)
   - FedRAMP: 24-36 months, $1M-2M (only if serious about government)

**Final Recommendation:** Design architecture for future SEV-SNP support (use KVM-compatible isolation), but do NOT implement until first enterprise customer demands it with committed contract. The technology is ready, the ROI is compelling, but customer demand must drive the investment timing.

---

**Next Document:** `security-by-phase.md` (detailed phased security implementation plan)
