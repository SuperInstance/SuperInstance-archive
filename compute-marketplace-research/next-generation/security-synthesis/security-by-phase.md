# Security Implementation by Phase
## Phased Security Roadmap with Risk Acceptance

**Date:** October 14, 2025
**Purpose:** Detailed phased security implementation balancing time-to-market with protection

---

## Executive Summary

This document provides a pragmatic phased security roadmap that balances **minimum viable security (MVP)** with **enterprise-grade protection (Scale)**. Each phase explicitly documents security capabilities, gaps, risks accepted, and triggers for moving to the next phase.

**Philosophy:** Don't over-engineer early, but design architecture to support future security enhancements without major rewrites.

---

## Phase 1: MVP Security (Months 1-6)

### Goal
Launch marketplace with **acceptable security for early adopters** while building revenue and user base.

### Security Stack

**Isolation:**
- ✅ **Hardened Docker (Tier 3 ONLY)** - Already implemented
  - Read-only root filesystem
  - Dropped capabilities
  - Seccomp profiles
  - AppArmor/SELinux
  - Resource limits (cgroups)

**Network Security:**
- ✅ **Network namespaces** - Linux kernel isolation
- ✅ **iptables firewall** - Basic ingress/egress rules
- ✅ **TLS 1.3** - All API communication encrypted

**Authentication & Access:**
- ✅ **JWT tokens** - API authentication
- ✅ **API key rotation** - 90-day expiration
- ✅ **Rate limiting** - 1,000 requests/hour per user

**Provider Verification:**
- ✅ **Entry benchmarking** - Automated on registration
- ✅ **Basic reputation** - Completion rate tracking
- ✅ **Resource limits** - CPU, memory, GPU quotas

**Monitoring:**
- ✅ **Prometheus metrics** - Basic monitoring
- ✅ **Structured logging** - JSON logs
- ✅ **Alerting** - PagerDuty integration

### Security Gaps Accepted

**Critical Gaps:**
- ❌ **No VM-level isolation** - Container escape possible (CVE-2025-9074)
- ❌ **No confidential computing** - Provider can inspect memory
- ❌ **No checkpoint encryption** - Checkpoint files readable by provider
- ❌ **No image scanning** - Malicious container images possible
- ❌ **No advanced network security** - iptables (not Cilium)

**Medium Gaps:**
- ❌ **No multi-tier isolation** - All users on Docker (no trust differentiation)
- ❌ **No GPU isolation** - Shared GPU memory visible across tenants
- ❌ **No fraud detection** - Basic reputation only
- ❌ **No penetration testing** - Informal security review only

### Risk Assessment

**Impact of Gaps:**
- **Container escape** → Full host compromise (affects all jobs on host)
- **Memory inspection** → IP theft, data exfiltration
- **Malicious images** → Cryptomining, backdoors
- **Shared GPU memory** → ML model theft

**Likelihood:**
- **Container escape:** MEDIUM (CVEs discovered regularly, but requires untrusted user)
- **Memory inspection:** LOW (requires malicious provider)
- **Malicious images:** LOW (early users are researchers, not attackers)
- **GPU memory:** LOW (limited multi-tenant GPU initially)

**Risk Acceptance Rationale:**
- Early adopters understand risks (researchers, not enterprises)
- Trust-based onboarding (manual vetting of first 100 users)
- Limited scale (< 1,000 jobs/month) reduces attack surface
- Revenue needed to fund Phase 2 security investment

**Suitable Customers:**
- ✅ Academic researchers (public datasets, published papers)
- ✅ Open-source ML projects (no proprietary IP)
- ✅ Individual developers (hobbyist projects)
- ❌ Enterprises (wait for Phase 2)
- ❌ Healthcare/Finance (wait for Phase 3)

### Cost

**Engineering:** $50K (2 engineers × 3 months × $100K/year salary)
- Hardening Docker (refinement of existing implementation)
- Entry benchmarking automation
- Basic reputation system
- Prometheus monitoring setup

**Infrastructure:** $0 (uses existing Docker infrastructure)

**Total:** $50K

### Success Metrics

- Zero container escapes from Tier 3 (acceptable for trusted users)
- < 1% provider fraud detection rate
- 99% job completion rate
- 100 users, 1,000 jobs/month
- $50K-100K monthly GMV

### Migration Trigger to Phase 2

**ANY of these conditions:**
1. > 10,000 jobs/month (scale demands better isolation)
2. First enterprise customer requests Firecracker (revenue opportunity)
3. Container escape detected (security incident)
4. Competitor launches with better isolation (competitive pressure)
5. > $500K monthly GMV (can afford Phase 2 investment)

---

## Phase 2: Production Security (Months 7-18)

### Goal
Enterprise-grade security for **regulated industries and sensitive workloads**.

### Security Stack (Additions to Phase 1)

**Multi-Tier Isolation:**
- ✅ **Firecracker microVMs (Tier 1)** - Untrusted users
  - KVM hardware virtualization
  - <100ms startup
  - 0-2% overhead
- ✅ **gVisor sandboxing (Tier 2)** - Verified users
  - Syscall filtering
  - 10-20% overhead
- ✅ **Hardened Docker (Tier 3)** - Trusted users
  - Existing implementation
  - Best performance

**Automated Tier Assignment:**
- ✅ **Reputation-based tiering** - Auto-upgrade/-downgrade
- ✅ **User opt-in/out** - Upgrade to Firecracker for premium

**Network Security:**
- ✅ **Cilium + eBPF** - Identity-based policies
  - 50-100% throughput improvement vs iptables
  - FQDN-based egress filtering
  - WireGuard encryption (<5% overhead)
- ✅ **Network policies** - Per-tenant isolation
- ✅ **Crypto mining blocking** - FQDN blocklists

**Supply Chain Security:**
- ✅ **Image scanning (Trivy)** - All user images scanned
- ✅ **Vulnerability database** - Daily updates
- ✅ **Signature verification** - Cosign for approved images

**Checkpoint Security:**
- ✅ **Checkpoint encryption** - AES-256 with user keys
- ✅ **Checkpoint signing** - Integrity verification
- ✅ **Remote storage** - Platform S3 (not provider disk)

**Advanced Monitoring:**
- ✅ **Falco runtime detection** - Anomalous behavior alerts
- ✅ **VictoriaMetrics** - High-scale metrics
- ✅ **Distributed tracing (Tempo)** - Request flow visibility

**Compliance:**
- ✅ **SOC 2 Type II preparation** - Audit controls
- ✅ **HIPAA readiness** - Encryption, access controls
- ✅ **Audit logs** - Immutable, tamper-proof

### Security Gaps Accepted

**Critical Gaps (from Phase 1) - NOW CLOSED:**
- ✅ Container escape (Firecracker Tier 1 prevents)
- ✅ Malicious images (Trivy scanning detects)
- ✅ Advanced network attacks (Cilium policies prevent)

**Remaining Gaps:**
- ❌ **No confidential computing** - Provider can still inspect memory (Tier 1/2/3)
- ❌ **No GPU TEE** - GPU memory visible to provider
- ❌ **No advanced fraud detection** - Basic ML models only
- ❌ **No bug bounty** - External security testing limited

### Risk Assessment

**Remaining Risks:**
- **Memory inspection (non-confidential VMs):** MEDIUM likelihood, HIGH impact
  - Mitigated by Firecracker (provider needs VM escape + hypervisor exploit)
  - Acceptable for non-sensitive workloads
- **GPU memory inspection:** MEDIUM likelihood, MEDIUM impact
  - Kata Containers provides VM isolation (harder than Tier 3)
  - MIG not yet implemented (multi-tenant GPU still shares memory)
- **Advanced fraud (provider oversubscription):** LOW likelihood, MEDIUM impact
  - Continuous monitoring detects (not prevents)

**Risk Acceptance Rationale:**
- Confidential computing requires $1M+ investment (wait for customer demand)
- GPU isolation with Kata sufficient for most workloads
- Fraud detection via monitoring acceptable (not prediction)

**Suitable Customers:**
- ✅ Enterprises (general, non-regulated)
- ✅ Sensitive but non-regulated data (trade secrets)
- ✅ ML model training (proprietary models, IP protection via Firecracker)
- ⚠️ Healthcare/Finance (acceptable IF non-confidential data)
- ❌ Government classified (wait for Phase 3)

### Cost

**Engineering:** $800K (7 engineers × 6 months × $140K/year avg)
- 3 systems engineers (Firecracker implementation)
- 2 security engineers (Cilium, image scanning, Falco)
- 1 network engineer (Cilium policies, WireGuard)
- 1 compliance specialist (SOC 2 preparation)

**Infrastructure:** $500K
- 50 bare metal servers for Firecracker ($15K × 50 = $750K amortized over 3 years = $250K/year)
- Cilium expertise (training, consulting: $50K)
- Trivy/Falco licenses (open-source, $0)
- S3 storage for checkpoints ($10K/year)
- Total first-year infra: $310K, ongoing: $100K/year

**Compliance:** $150K (SOC 2 Type II audit preparation)

**Total:** $1.46M first year, $950K ongoing

### Success Metrics

- Zero successful container escapes (all tiers)
- < 0.1% cross-tenant network access attempts
- 100% of untrusted workloads on Firecracker (Tier 1)
- > 95% malicious image detection rate
- 5+ enterprise customers acquired
- $5M-10M monthly GMV

### Migration Trigger to Phase 3

**ANY of these conditions:**
1. First healthcare/finance customer demands SEV-SNP ($1M+ contract)
2. Competitive pressure (Vast.ai launches confidential computing)
3. > 100,000 jobs/month (scale demands optimization)
4. > $50M annual revenue (can afford Phase 3 investment)
5. Compliance certification required (HIPAA, PCI-DSS)

---

## Phase 3: Enterprise-Grade Defense-in-Depth (Months 19+)

### Goal
**Maximum security for regulated industries** (healthcare, finance, government) with confidential computing and multiple compliance certifications.

### Security Stack (Additions to Phase 2)

**Confidential Computing:**
- ✅ **AMD SEV-SNP** - VM memory encryption
  - Provider cannot inspect memory (hardware-enforced)
  - Remote attestation (user verifies platform integrity)
  - 2-10% performance overhead
- ✅ **H100 GPU TEE** - GPU memory encryption
  - Encrypted CPU↔GPU transfers
  - Protects proprietary ML models
  - 5-15% overhead
- ✅ **Attestation service** - Intel Trust Authority or self-hosted
- ✅ **Key Management System** - Customer-managed keys (BYOK)

**GPU Security Optimization:**
- ✅ **NVIDIA MIG** - Hardware GPU partitioning
  - 7 isolated instances per A100
  - QoS guarantees
  - Better density (7x tenants/GPU)
- ✅ **Kata Containers for GPU** - VM isolation for GPU workloads

**Advanced Fraud Detection:**
- ✅ **ML-based anomaly detection** - Behavioral analysis
  - Detect cryptomining patterns
  - Identify benchmark manipulation
  - Flag suspicious resource usage
- ✅ **Link analysis** - Identify coordinated fraud rings
- ✅ **Device fingerprinting** - Prevent multi-accounting

**Security Operations:**
- ✅ **Bug bounty program** - External security researchers
  - $500-$50K bounties (depending on severity)
  - Continuous security testing
- ✅ **Penetration testing** - Annual third-party audits
  - $50K-100K per audit
- ✅ **Chaos engineering** - Resilience testing
  - Gremlin, LitmusChaos
  - Monthly chaos experiments
- ✅ **SIEM (Security Information and Event Management)** - Centralized security monitoring
  - Splunk, Elastic Security
  - Correlation of security events across platform

**Compliance Certifications:**
- ✅ **HIPAA** - Healthcare
  - 12-18 months, $150K
- ✅ **PCI-DSS Level 1** - Payment card industry
  - 18-24 months, $200K
- ✅ **FedRAMP High** - US Government (optional)
  - 24-36 months, $1M-2M

### Security Gaps Accepted

**All critical gaps from Phase 1 and 2 now closed.**

**Remaining Risks (Low Priority):**
- **Side-channel attacks** - Spectre, Meltdown variants
  - Mitigation: Too expensive ($2M+ for constant-time everything)
  - Acceptance: Low likelihood, monitor research
- **Zero-day exploits** - Unknown vulnerabilities
  - Mitigation: Bug bounty reduces window
  - Acceptance: Impossible to prevent completely
- **Insider threats** - Malicious employees
  - Mitigation: SIEM, audit logs, background checks
  - Acceptance: Trust employees (but verify)
- **Advanced Persistent Threats (APTs)** - Nation-state actors
  - Mitigation: Too expensive ($5M+ for threat intel, SOC)
  - Acceptance: Not likely target (focus on common threats)

**Risk Acceptance Rationale:**
- Diminishing returns (99.9% security vs 99.99% costs 10x more)
- Focus on high-likelihood threats (not theoretical APTs)
- Bug bounty + pen testing catch most issues

**Suitable Customers:**
- ✅ Healthcare (HIPAA-compliant)
- ✅ Finance (PCI-DSS-compliant)
- ✅ Government (FedRAMP, if certified)
- ✅ Pharmaceutical (trade secrets, confidential computing)
- ✅ Legal (attorney-client privilege, confidential VMs)

### Cost

**Engineering:** $600K (5 engineers × 6 months × $200K/year avg)
- 3 systems engineers (SEV-SNP, GPU TEE)
- 2 security engineers (bug bounty, pen testing, SIEM)

**Infrastructure:** $1M
- 100 AMD EPYC servers with SEV-SNP ($15K × 100 = $1.5M amortized over 3 years = $500K/year)
- 20 H100 GPUs ($30K × 20 = $600K amortized over 3 years = $200K/year)
- Attestation service (self-hosted: $50K setup, $10K/year ongoing)
- SIEM (Splunk: $100K/year)
- Total first-year infra: $860K, ongoing: $500K/year

**Compliance:** $350K
- HIPAA audit: $150K
- PCI-DSS Level 1 audit: $200K
- Ongoing compliance: $50K/year

**Security Operations:** $200K/year
- Bug bounty program: $100K/year (payouts)
- Penetration testing: $75K/year (annual)
- Chaos engineering tools: $25K/year

**Total:** $2.01M first year, $1.25M ongoing

### Success Metrics

- Zero memory inspection incidents (SEV-SNP)
- > 10% of GPU revenue from confidential computing
- HIPAA certification achieved
- PCI-DSS Level 1 certification achieved
- > 20 enterprise customers (regulated industries)
- > 10 critical vulnerabilities found via bug bounty
- $50M+ annual revenue from enterprise segment

### Steady State (Years 3+)

**Ongoing Costs:**
- Engineering: $1.2M/year (6 FTE security engineers × $200K)
- Infrastructure: $500K/year (amortized hardware + cloud costs)
- Compliance: $150K/year (annual audits, certifications)
- Security operations: $200K/year (bug bounty, pen tests)
- **Total:** $2.05M/year

**Ongoing Activities:**
- Quarterly penetration testing ($75K/year)
- Monthly chaos engineering experiments
- Continuous bug bounty ($100K/year payouts)
- Annual compliance audits (SOC 2, HIPAA, PCI-DSS)
- Security research (monitor CVEs, academic papers)
- Incident response drills (quarterly)

---

## Phase Comparison Matrix

| Aspect | Phase 1 (MVP) | Phase 2 (Production) | Phase 3 (Enterprise) |
|--------|---------------|----------------------|----------------------|
| **Timeline** | Months 1-6 | Months 7-18 | Months 19+ |
| **Investment** | $50K | $1.46M | $2.01M |
| **Isolation** | Docker only | Docker + gVisor + Firecracker | + SEV-SNP + GPU TEE |
| **Network** | iptables | Cilium + eBPF | + WireGuard encrypted |
| **Supply Chain** | None | Trivy scanning | + Signature verification |
| **Confidential Computing** | None | None | AMD SEV-SNP + H100 TEE |
| **Compliance** | None | SOC 2 prep | HIPAA + PCI-DSS + FedRAMP (opt) |
| **Security Ops** | Basic | Falco monitoring | Bug bounty + pen tests |
| **Suitable Customers** | Researchers, hobbyists | Enterprises (non-regulated) | Healthcare, finance, govt |
| **Risk Level** | MEDIUM-HIGH | LOW-MEDIUM | LOW |
| **GMV Target** | $50K-100K/mo | $5M-10M/mo | $50M+/mo |

---

## Migration Checklists

### Phase 1 → Phase 2 Migration

**Pre-Migration (Month 6):**
- [ ] Firecracker architecture design finalized
- [ ] Bare metal servers ordered (50 units, 8-week lead time)
- [ ] 3 systems engineers hired (Rust, KVM expertise)
- [ ] gVisor integration tested in staging
- [ ] Reputation scoring algorithm implemented
- [ ] Tier assignment logic coded
- [ ] Customer communication plan (warn of changes)

**Month 7 (Infrastructure Setup):**
- [ ] Bare metal servers deployed in datacenter
- [ ] KVM/QEMU installed and configured
- [ ] Firecracker binaries installed (v1.9.1+)
- [ ] Network infrastructure (TAP devices, bridging)
- [ ] Storage infrastructure (S3 for checkpoints)
- [ ] Monitoring (Prometheus exporters for Firecracker)

**Month 8-9 (Software Integration):**
- [ ] Firecracker API integration (REST API for VM lifecycle)
- [ ] gVisor integration (runsc runtime)
- [ ] Automated tier assignment (reputation → isolation tech)
- [ ] Cilium deployment (eBPF network policies)
- [ ] Trivy image scanning (integration with Docker registry)
- [ ] Checkpoint encryption (AES-256, user-managed keys)

**Month 10 (Testing):**
- [ ] Security testing (try to escape Firecracker, gVisor)
- [ ] Performance benchmarking (CPU, GPU, network)
- [ ] Reliability testing (checkpoint/restart, VM migration)
- [ ] Chaos engineering (simulate failures)

**Month 11 (Gradual Rollout):**
- [ ] Week 1: New users only (Tier 1)
- [ ] Week 2: 10% of verified users (Tier 2)
- [ ] Week 3: 50% of verified users
- [ ] Week 4: 100% rollout

**Month 12 (Optimization):**
- [ ] Performance tuning (Firecracker boot time, gVisor overhead)
- [ ] Cost optimization (bin packing, spot instances)
- [ ] User feedback incorporation
- [ ] SOC 2 Type II audit kickoff

**Rollback Plan:**
- [ ] Feature flags (toggle Firecracker/gVisor off)
- [ ] Docker infrastructure maintained (parallel running)
- [ ] Gradual migration (not big-bang, can pause/reverse)

---

### Phase 2 → Phase 3 Migration

**Pre-Migration (Month 18):**
- [ ] First enterprise customer commitment ($1M+ contract)
- [ ] AMD EPYC servers ordered (100 units, 12-week lead time)
- [ ] H100 GPUs ordered (20 units, 16-week lead time due to shortages)
- [ ] Security engineers hired (SEV-SNP expertise)
- [ ] HIPAA/PCI-DSS audit firm selected
- [ ] Compliance consultants engaged

**Month 19-21 (Hardware Deployment):**
- [ ] AMD EPYC servers deployed (new regions or upgrade existing)
- [ ] H100 GPUs installed (dedicated confidential computing nodes)
- [ ] BIOS/firmware updates (SEV-SNP enablement)
- [ ] Network infrastructure (isolated confidential VLAN)

**Month 22-24 (Software Integration):**
- [ ] QEMU 6.2+ with SEV-SNP support
- [ ] Linux kernel 5.19+ (host and guest)
- [ ] OVMF firmware (UEFI for confidential VMs)
- [ ] Attestation service (Intel Trust Authority integration)
- [ ] KMS integration (AWS KMS, Azure Key Vault, HashiCorp Vault)
- [ ] H100 GPU TEE drivers and configuration

**Month 25-27 (Compliance):**
- [ ] HIPAA gap assessment
- [ ] PCI-DSS gap assessment
- [ ] Remediation (implement missing controls)
- [ ] Internal audit (pre-audit readiness)
- [ ] External audit (QSA for PCI-DSS, HIPAA auditor)

**Month 28-30 (Pilot):**
- [ ] Beta test with first enterprise customer
- [ ] Remote attestation end-to-end testing
- [ ] Performance benchmarking (confidential VMs vs standard)
- [ ] Security audit (third-party pen test)
- [ ] Customer feedback incorporation

**Month 31-33 (General Availability):**
- [ ] Gradual rollout to all regions
- [ ] Marketing campaign ("Enterprise-grade confidential computing")
- [ ] Sales enablement (train sales team on SEV-SNP value prop)
- [ ] Documentation (customer guides, API docs, attestation flow)

**Month 34-36 (Optimization):**
- [ ] Performance tuning (reduce SEV-SNP overhead)
- [ ] Cost optimization (better hardware utilization)
- [ ] Compliance certification maintenance
- [ ] Annual security audit

---

## Risk Acceptance by Phase

### Phase 1: High-Risk Acceptance

**Accepted Risks:**
- Container escape (CVE-2025-9074 class vulnerabilities)
- Memory inspection by provider
- Malicious container images
- Cross-tenant GPU memory access
- No compliance certifications

**Justification:**
- Early adopters understand risks
- Manual user vetting (trust-based)
- Limited scale (<1,000 jobs/month)
- Revenue needed to fund Phase 2

**Communication:**
- Terms of Service: "Platform suitable for non-sensitive workloads only"
- Docs: "Security roadmap: Firecracker coming in Phase 2"
- Customer emails: "We recommend Docker for trusted users only"

---

### Phase 2: Medium-Risk Acceptance

**Accepted Risks:**
- Memory inspection by provider (non-confidential VMs)
- GPU memory visible to provider
- Advanced fraud (undetected)

**Justification:**
- Firecracker raises bar for memory inspection (requires VM escape + hypervisor exploit)
- GPU isolation via Kata Containers acceptable for most workloads
- Fraud detection via monitoring (not prediction)

**Communication:**
- Terms of Service: "Firecracker VMs protect against container escape, but memory encryption requires Phase 3"
- Docs: "Confidential computing roadmap: SEV-SNP coming for enterprise customers"
- Sales: "We offer enterprise-grade isolation, with confidential computing available for regulated industries (coming Q4)"

---

### Phase 3: Low-Risk Acceptance

**Accepted Risks:**
- Side-channel attacks (Spectre variants)
- Zero-day exploits
- Advanced Persistent Threats (nation-state)

**Justification:**
- Diminishing returns (99.9% → 99.99% security costs 10x more)
- Side-channels require proximity, expertise (low likelihood)
- Zero-days addressed via bug bounty (reduce window)
- APTs unlikely to target P2P compute marketplace (not high-value target)

**Communication:**
- Terms of Service: "Platform designed for enterprise security, but no system is 100% secure"
- Docs: "We employ defense-in-depth, but accept some residual risks (side-channels, zero-days)"
- Sales: "We meet HIPAA/PCI-DSS requirements, with ongoing security testing"

---

## Conclusion

This phased security roadmap balances **pragmatism** (launch fast, iterate) with **prudence** (don't under-engineer critical security). Each phase explicitly documents:
- Security capabilities
- Gaps accepted
- Risks and mitigations
- Suitable customers
- Investment required
- Migration triggers

**Key Principles:**
1. **Phase 1:** Minimum viable security (acceptable for early adopters)
2. **Phase 2:** Production-grade security (enterprise-ready)
3. **Phase 3:** Defense-in-depth (regulated industries)

**Success Factors:**
- Clear communication of risks at each phase
- Gradual migration (not big-bang)
- Customer demand drives timing (not speculation)
- ROI justifies investment (revenue > cost)

---

**Next Document:** `security-operations.md` (testing strategy, compliance roadmap, monitoring, incident response)
