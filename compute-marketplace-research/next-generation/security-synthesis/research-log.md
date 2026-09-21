# Security Architecture Research Log
## Compute Marketplace Security Synthesis

**Date:** October 14, 2025
**Researcher:** Agent 3 - Security Architecture Synthesis
**Mission:** Compare and merge two security visions for next-generation compute marketplace

---

## Executive Summary

This research synthesizes **Vision A (Three-Tier Security Model)** from local technical architecture research with **Vision B (Five-Layer Defense-in-Depth)** from the Production-Grade P2P document. The goal is to create a unified security architecture that balances time-to-market, cost, and protection against real threats.

**Key Finding:** Both visions are complementary rather than contradictory. Vision A provides a pragmatic phased approach focused on isolation tiers, while Vision B offers comprehensive defense-in-depth with production-grade technologies. The synthesis combines Vision A's trust-based tiering with Vision B's workload-specific technology selection and comprehensive threat modeling.

---

## Research Process

### Phase 1: Document Analysis (Completed)

**Vision A Sources:**
- `/home/activeloguser/compute-marketplace-research/technical-architecture/EXECUTIVE_SUMMARY.md` (533 lines)
- `/home/activeloguser/compute-marketplace-research/technical-architecture/research-findings.md` (1,789 lines)
- `/home/activeloguser/compute-marketplace-research/technical-architecture/firecracker-setup-guide.md` (1,063 lines)
- `/home/activeloguser/compute-marketplace-research/technical-architecture/gvisor-integration-guide.md` (1,006 lines)
- `/home/activeloguser/compute-marketplace-research/technical-architecture/gpu-passthrough-guide.md` (1,043 lines)
- `/home/activeloguser/compute-marketplace-research/technical-architecture/checkpoint-restart-guide.md` (1,428 lines)

**Vision B Sources:**
- `/home/activeloguser/Production-GradeP2PComputeMark.md` (217 lines, comprehensive)

**Total Documentation Analyzed:** ~6,000+ lines of technical architecture

### Phase 2: Security Model Comparison

**Vision A: Three-Tier Trust-Based Model**
- Focus: User trust level determines isolation technology
- Tier 1: Firecracker microVMs (untrusted/new users)
- Tier 2: gVisor sandboxing (verified users)
- Tier 3: Hardened Docker (trusted users)
- Philosophy: Progressive trust with graduated security overhead
- Timeline: 6-9 months for Tier 1+2, Tier 3 already complete

**Vision B: Five-Layer Defense-in-Depth**
- Focus: Multiple security boundaries with workload-specific selection
- Layer 1: CRI-O runtime (minimal attack surface)
- Layer 2: Workload isolation (gVisor for CPU, Firecracker for serverless, Kata for GPU)
- Layer 3: Cilium + eBPF network policies
- Layer 4: AMD SEV-SNP confidential computing
- Layer 5: Application security (attestation, verification)
- Philosophy: Defense-in-depth with no single point of failure

### Phase 3: Gap Analysis

**Vision A Strengths:**
- Clear phased implementation roadmap
- Pragmatic about MVP vs enterprise needs
- Acknowledges existing Docker implementation (Tier 3)
- DMTCP checkpoint/restart for reliability (<4 second recovery)
- Confidential computing as Phase 3 differentiator (12-18 months)

**Vision A Gaps:**
- No container runtime specification (assumes Docker/containerd)
- Limited network security detail
- Basic threat model (container escape, resource abuse, provider fraud)
- Checkpoint security implications not deeply analyzed
- GPU security focuses on passthrough/MIG, not isolation layers

**Vision B Strengths:**
- Comprehensive threat model (4 adversary types)
- Container runtime specified (CRI-O for security)
- Advanced network security (Cilium + eBPF)
- Confidential computing integrated into production (not just Phase 3)
- GPU security includes Kata Containers (only isolation supporting GPU)
- Security operations roadmap (pen testing, bug bounty, chaos engineering)

**Vision B Gaps:**
- No trust-based tiering (all workloads treated equally secure)
- Complexity may delay MVP
- Cost implications of CRI-O, Cilium, SEV-SNP not analyzed
- Checkpoint/restart uses CRIU (security concerns with SYS_PTRACE capability)

---

## Vision A: Three-Tier Security Model (Deep Dive)

### Architecture Philosophy

Vision A prioritizes **pragmatic phased deployment** aligned with business maturity:
- Start with acceptable security (hardened Docker)
- Add enterprise-grade isolation as revenue grows
- Balance security investment with customer willingness to pay
- Use trust signals to reduce unnecessary overhead

### Tier 1: Firecracker MicroVMs (Untrusted Workloads)

**Technology:**
- AWS Firecracker (KVM-based microVM manager)
- 50,000 lines of Rust (vs QEMU's 1.4M lines)
- Hardware virtualization provides complete isolation

**Performance:**
- Startup: <100ms (125ms typical)
- Memory overhead: <5 MiB per microVM
- CPU overhead: 0-2% (near-native)
- Throughput: Thousands of microVMs per second per host

**Security Model:**
- Each microVM runs its own kernel (no shared kernel)
- Hardware virtualization isolates workloads from host
- Jailer component: seccomp-bpf, cgroups, chroot isolation
- Minimal attack surface: 40 syscalls vs 400+ in standard Linux
- Guest kernel explicitly treated as untrusted

**Use Cases:**
- New users without established reputation
- Untrusted code from unknown sources
- Sensitive workloads requiring maximum isolation
- Short-lived functions and serverless workloads

**Implementation Complexity:**
- Difficulty: 8/10
- Timeline: 6-9 months with 3-4 engineers
- Infrastructure: Bare metal hosts, KVM support required
- No nested virtualization (must run on physical hardware)

**Critical CVE Context:**
- **CVE-2025-9074** (Docker Desktop container escape, CVSS 9.3)
  - Containers can access Docker Engine API without auth
  - Can bind host filesystem and achieve full compromise
  - Patched in Docker Desktop 4.44.3 (Aug 20, 2025)
  - **Implication:** Docker alone insufficient for untrusted workloads

- **CVE-2025-23266** (NVIDIAScape container escape)
  - Demonstrates ongoing container isolation weakness
  - gVisor and Firecracker immune to this class of vulnerabilities

**Recommendation Rationale:**
- Container escapes are NOT theoretical—they're happening in 2025
- Hardware virtualization is only proven defense
- Performance overhead minimal (0-2%)
- Battle-tested at AWS scale (7+ years production)

### Tier 2: gVisor Sandboxing (Verified Users)

**Technology:**
- User-space kernel implementing Linux in memory-safe Go
- Intercepts syscalls and emulates them in userspace
- Shields host Linux kernel from sandboxed applications

**Performance:**
- Overall overhead: 10-20% typical (workload-dependent)
- CPU-bound: Minimal overhead (API servers, data pipelines)
- I/O-heavy: Degraded performance (databases)
- Network-heavy: Degraded performance (load balancers)
- Startup: ~seconds (slower than Firecracker)

**Security Model:**
- Application kernel isolation through syscall interception
- Reduces kernel attack surface to <20 syscalls
- Protects against most Linux kernel CVEs
- Each application gets isolated kernel implementation
- Defense against container escape vulnerabilities

**Use Cases:**
- Verified users with established track record
- Moderate trust level workloads
- CPU-intensive workloads (ML inference, data processing)
- Workloads where 10-20% overhead acceptable

**Implementation Complexity:**
- Difficulty: 6/10
- Timeline: Integrated with Tier 1 (6-9 months)
- Infrastructure: Compatible with standard containers
- Works in nested virtualization (can run in cloud VMs)

**GPU Support:**
- nvproxy enables GPU access in gVisor
- NVIDIA driver proxy for secure GPU operations
- Suitable for inference workloads
- NOT suitable for multi-tenant GPU sharing

**Recommendation Rationale:**
- Balances security with performance
- Users with reputation don't need VM overhead
- Defense-in-depth without hardware virtualization
- Compatible with existing container workflows

### Tier 3: Hardened Docker (Trusted Users)

**Technology:**
- Standard Docker containers with security hardening
- Already implemented in local codebase (TypeScript, 1,702 lines)
- Production-ready foundation

**Security Hardening:**
- Read-only root filesystem
- Drop all capabilities by default
- Seccomp profiles (default action: SCMP_ACT_ERRNO)
- AppArmor profiles (docker-default)
- SELinux contexts (optional)
- No new privileges flag
- IPC/PID isolation
- Network isolation modes

**Resource Limits:**
- CPU: cores, shares, quota, period, cpuset
- Memory: limit, reservation, swap limit, OOM kill disable
- Storage: size, read/write IOPS, disk quota
- Network: bandwidth, latency, connections

**Performance:**
- Near-native (1-3% overhead)
- Minimal memory overhead
- Instant startup
- Best performance of all tiers

**Use Cases:**
- Verified organizations with long-term relationship
- High-volume users with established reputation
- Performance-critical workloads
- Trusted proprietary code

**Security Limitations:**
- Shared kernel (vulnerable to kernel exploits)
- Container escape vulnerabilities (CVE-2025-9074)
- Requires trust in user not to exploit weaknesses

**Recommendation Rationale:**
- Already implemented (4,000+ lines production code exists)
- Acceptable for trusted users
- Provides best performance for high-value customers
- Cost-effective for scale

### Trust Progression Model

**User Journey:**
1. **New User** → Tier 1 (Firecracker)
   - Unknown reputation
   - First 10 jobs or 30 days
   - Highest isolation, slightly higher pricing

2. **Established User** → Tier 2 (gVisor)
   - 10+ successful jobs
   - >90% completion rate
   - Balanced isolation/performance

3. **Trusted Organization** → Tier 3 (Docker)
   - 100+ jobs or $10K+ spend
   - >95% completion rate
   - Long-term contract
   - Lowest overhead, best pricing

**Automatic Tier Migration:**
- Reputation scoring determines tier
- Automated tier upgrades based on metrics
- Manual review for tier downgrades (fraud prevention)
- Users can request higher security tier (pay premium)

### Confidential Computing (Phase 3 Differentiator)

**Technology Options:**
- **Intel SGX** (Software Guard Extensions)
  - Application-level enclaves
  - Process-based confidential computing
  - Limited enclave memory (128MB-256MB)
  - More mature, wider hardware support

- **AMD SEV-SNP** (Secure Encrypted Virtualization)
  - VM-level memory encryption
  - Protects entire VM from hypervisor
  - Larger memory support
  - Hardware attestation

**Business Impact:**
- Opens $10B+ enterprise market
- 2-3x premium pricing vs standard tiers
- Addresses #1 user concern: "Can't guarantee host isn't logging my data"
- Enables HIPAA, financial services, government contracts
- Competitive moat (Vast.ai, Golem, Akash cannot offer)

**Timeline:**
- 12-18 months after Tier 1/2 complete
- Requires specialized hardware
- Complex attestation implementation
- Enterprise customer pilot required

**Use Cases:**
- Healthcare data processing (HIPAA)
- Financial services (PCI-DSS)
- Proprietary ML model training
- Government workloads (FedRAMP)
- Legal/IP-sensitive computations

**Recommendation:** Phase 3 feature, not MVP requirement

### DMTCP Checkpoint/Restart (Reliability Advantage)

**Technology:**
- Distributed MultiThreaded CheckPointing
- Library-level checkpoint/restore
- Transparent to application (no code changes)

**Performance:**
- Restart: <4 seconds even for 64-node computations
- Checkpoint overhead: <1% runtime
- Storage: Compressed checkpoints (2-3x reduction)

**Capabilities:**
- Preserves application state to disk
- Resumes at later time or different location
- Supports MPI, OpenMP, MATLAB, Python, R
- No kernel modifications required
- Battle-tested at NERSC supercomputers

**Competitive Advantage:**
- **Vast.ai:** No checkpointing = full job restart on failure
- **Golem:** Redundancy-based = 2-3x compute cost
- **This approach:** Best reliability/cost ratio

**Implementation:**
- Timeline: 8-12 months
- Team: 4-5 engineers
- Integration with orchestration system
- Hourly automatic checkpoints for long jobs

**Recommendation:** Critical for marketplace competitiveness

---

## Vision B: Five-Layer Defense-in-Depth (Deep Dive)

### Architecture Philosophy

Vision B prioritizes **comprehensive security through multiple independent layers**:
- No single point of failure
- Each layer defends against different attack vectors
- Workload type determines isolation technology (not just trust)
- Production-grade from day one (no "acceptable security" compromise)

### Layer 1: Container Runtime Security (CRI-O)

**Technology:**
- CRI-O: Lightweight OCI runtime for Kubernetes
- Minimal attack surface vs containerd
- SELinux enforcement by default
- No unnecessary features (daemon-less)

**Performance:**
- 1% performance overhead vs containerd
- Lower memory footprint
- Faster startup times
- Better resource efficiency

**Security Benefits:**
- Smaller codebase = fewer vulnerabilities
- SELinux mandatory access control
- No Docker daemon (reduces attack surface)
- OCI-compliant (standardized)

**Complexity Trade-off:**
- Less mature tooling than Docker/containerd
- Smaller community
- Fewer integration examples
- Requires Kubernetes or CRI-compatible orchestrator

**Analysis:**
- **Is CRI-O worth it?** Depends on team expertise
- **For MVP:** Start with containerd (larger ecosystem)
- **For Scale:** Migrate to CRI-O when team has Kubernetes experience
- **Security gain:** Real but incremental (1-2% security improvement)

**Recommendation:** Optional for MVP, consider for Phase 2

### Layer 2: Workload-Specific Isolation

**Philosophy:** Isolation technology driven by technical requirements, not just trust

**gVisor: Untrusted CPU Workloads**
- Use case: Batch processing, API services, data pipelines
- Overhead: 3-30% (workload-dependent)
- Syscalls exposed: 68 vs 350 in standard containers
- Best for: CPU-intensive with moderate I/O

**Firecracker: Serverless Functions**
- Use case: Short-lived functions, event-driven workloads
- Boot time: 125ms (fastest cold start)
- Memory: <5MiB overhead
- Best for: Sub-second execution, high-frequency invocation

**Kata Containers: GPU Workloads**
- Use case: ML training, rendering, GPU computing
- **Critical insight:** Only isolation technology supporting GPU passthrough
- Performance: Similar to Firecracker (VM-level)
- Best for: Any workload requiring GPU access with isolation

**Decision Matrix:**

| Workload Type | Trust Level | Isolation Technology | Rationale |
|---------------|-------------|---------------------|-----------|
| CPU batch | Untrusted | gVisor | Syscall filtering, good CPU performance |
| Serverless function | Any | Firecracker | Fast boot, minimal overhead |
| GPU training | Untrusted | Kata Containers | **Only option with GPU + isolation** |
| GPU training | Trusted | Bare metal GPU passthrough | Maximum performance |
| CPU interactive | Trusted | Hardened Docker | Lowest latency |
| Distributed MPI | Trusted | Hardened Docker + DMTCP | Checkpoint support |

**Synthesis with Vision A:**
- Combine trust level AND workload type
- Example: Untrusted user + GPU → Kata (forced by technical requirement)
- Example: Trusted user + GPU → Choice of Kata (security) or passthrough (performance)
- Example: Untrusted user + CPU → Choice of gVisor (performance) or Firecracker (maximum isolation)

**Recommendation:** Adopt workload-based selection within each trust tier

### Layer 3: Network Security (Cilium + eBPF)

**Technology:**
- Cilium: eBPF-based networking and security
- Identity-based policies (not IP-based)
- Kernel-level enforcement with BPF programs

**Performance Benefits:**
- 50-100% throughput improvement vs iptables
- Sub-microsecond policy enforcement
- Scales to 100,000+ pods per cluster
- <1ms latency overhead

**Security Features:**
- **Tenant isolation:** Cryptographic identities per workload
- **FQDN-based egress filtering:** Control external destinations
- **WireGuard encryption:** <5% overhead for node-to-node traffic
- **L7 policy enforcement:** HTTP/gRPC/Kafka protocol-aware
- **Network visibility:** Flow logs for all connections

**Implementation Complexity:**
- Requires Linux kernel 4.9.17+ with eBPF support
- Learning curve for eBPF programming
- Debugging more complex than iptables
- Requires Kubernetes or similar orchestrator

**Cost-Benefit Analysis:**

**For MVP (Months 1-6):**
- **Recommendation:** Start with iptables
- **Rationale:** Simpler, well-understood, sufficient for <1,000 jobs/day
- **Cost:** $0 (included in Linux)
- **Risk:** Performance bottleneck at scale

**For Growth (Months 7-18):**
- **Recommendation:** Migrate to Cilium
- **Rationale:** Performance becomes critical, tenant isolation essential
- **Cost:** ~$50K/year for expertise (training, consulting)
- **Trigger:** >10,000 concurrent jobs or >1Gbps network throughput

**For Scale (Months 19+):**
- **Recommendation:** Cilium + Hubble (observability)
- **Rationale:** Network visibility critical for debugging, compliance
- **Cost:** Included (open source)

**Recommendation:** Not essential for MVP, high-value for production

### Layer 4: Confidential Computing (AMD SEV-SNP)

**Technology:**
- AMD SEV-SNP (Secure Encrypted Virtualization - Secure Nested Paging)
- VM-level memory encryption
- Protects against malicious hypervisor/provider

**Performance:**
- Overhead: 2-10% (workload-dependent)
- Memory encryption: AES-128
- Negligible impact on CPU-bound workloads
- Higher impact on memory-intensive workloads

**Security Guarantees:**
- VM memory encrypted (protects from physical attacks)
- Hypervisor cannot inspect memory
- DMA attacks mitigated
- Remote attestation via AMD Secure Processor

**Attestation Flow:**
1. Compute job requests attestation
2. Workload generates cryptographic evidence via TEE
3. Attestation service verifies signatures, platform certificates, TCB versions
4. Service issues JWT token
5. Client validates token against policy
6. If valid, client releases encryption keys
7. Workload processes data in trusted execution environment

**Use Cases:**
- Sensitive healthcare data (HIPAA)
- Financial transactions (PCI-DSS)
- Proprietary ML models (IP protection)
- Government workloads (classified data)
- Multi-tenant environments (untrusted providers)

**Threat Model:**
- **Protects against:** Malicious provider with physical access
- **Protects against:** Hypervisor/kernel compromise
- **Protects against:** Memory inspection attacks
- **Does NOT protect against:** Application-level vulnerabilities
- **Does NOT protect against:** Side-channel attacks (speculative execution)

**Cost-Benefit Analysis:**

**When to implement SEV-SNP?**

**MVP (Months 1-6):**
- **Recommendation:** Skip
- **Rationale:** Too complex, too expensive, no customer demand yet
- **Cost:** $100K+ (specialized hardware, engineering)
- **Risk accepted:** Provider can inspect memory

**Growth (Months 7-18):**
- **Recommendation:** Add for enterprise customers who demand it
- **Rationale:** Unlocks regulated industries (healthcare, finance)
- **Cost:** $200K (hardware refresh, implementation)
- **Revenue unlock:** $10M+ (enterprise contracts with 2-3x pricing premium)

**Scale (Months 19+):**
- **Recommendation:** Standard offering for all sensitive workloads
- **Rationale:** Table stakes for enterprise market
- **Cost:** Amortized over fleet (hardware refresh cycle)

**Recommendation:** Phase 2 feature for enterprise customers, not MVP

### Layer 5: Application Security

**Workload Verification:**
- Container image scanning (Trivy/Clair)
- Signature verification (Sigstore/Cosign)
- SBOM (Software Bill of Materials) generation
- Vulnerability database integration

**Runtime Protection:**
- Falco: Runtime threat detection
- Anomalous behavior detection
- Syscall monitoring
- Network anomaly detection

**Attestation:**
- Workload identity verification
- Platform integrity checks
- Policy enforcement before execution
- Continuous verification during runtime

**Recommendation:** Essential for production, phase into MVP

---

## Key Security Insights

### 1. Container Runtimes: CRI-O vs Containerd

**Vision A:** Doesn't specify (implies Docker/containerd)
**Vision B:** Specifies CRI-O for minimal attack surface

**Analysis:**
- **Security improvement:** CRI-O 1-2% more secure (smaller codebase, SELinux default)
- **Operational complexity:** CRI-O requires Kubernetes expertise
- **Ecosystem maturity:** Containerd has larger community, more examples
- **Performance:** CRI-O 1% faster in benchmarks
- **Cost:** Training and expertise acquisition: $25K-50K

**Synthesis Recommendation:**
- **Phase 1 (MVP):** Use containerd
  - Rationale: Faster to market, larger community, Docker compatibility
  - Risk accepted: Slightly larger attack surface

- **Phase 2 (Growth):** Evaluate migration to CRI-O
  - Trigger: Team has Kubernetes experience, >10,000 jobs/day
  - Benefit: 1-2% security improvement, better SELinux integration

- **Phase 3 (Scale):** CRI-O for new regions, containerd for existing
  - Rationale: Don't disrupt production, but adopt for greenfield

### 2. Workload Isolation: Trust vs Workload Type

**Vision A:** Trust-based tiers (user reputation determines isolation)
**Vision B:** Workload-based selection (technical requirements determine isolation)

**Synthesis:** **Combine both approaches**

**Decision Matrix:**

```
                    CPU Workload              GPU Workload              Serverless
Untrusted User      gVisor (default)          Kata Containers*          Firecracker
                    Firecracker (max iso)     (ONLY option)             (ONLY option)

Verified User       gVisor (balanced)         Kata or Passthrough       Firecracker
                    Docker (opt-in)           (user choice)

Trusted User        Docker (default)          Passthrough (default)     Firecracker
                    gVisor (opt-in)           Kata (opt-in for iso)     (or Docker for long-lived)
```

*Kata Containers is the ONLY isolation technology supporting GPU passthrough

**Key Insights:**
- GPU workloads FORCE technical constraints (Kata required for isolation)
- Serverless FORCES Firecracker (only sub-second boot option)
- CPU workloads have FLEXIBILITY (can trade security vs performance)

**Pricing Strategy:**
- Firecracker/Kata: +10% (isolation overhead)
- gVisor: +5% (moderate overhead)
- Docker: Baseline (best performance)
- User can pay premium for higher isolation even if trusted

### 3. GPU Security Architecture

**Vision A Approach:**
- GPU passthrough (dedicated, 98-100% performance)
- NVIDIA MIG for multi-tenancy (later phase)
- SR-IOV as alternative
- Emphasis: Performance through dedication

**Vision B Approach:**
- Kata Containers (only isolation supporting GPU)
- NVIDIA vGPU with SR-IOV (5-15% overhead)
- NVIDIA MIG on A100/H100 (hardware partitioning)
- H100 GPU TEEs for confidential computing
- Emphasis: Multi-tenancy and isolation

**Synthesis: Phased GPU Security**

**Phase 1 (MVP):**
- **Technology:** Dedicated GPU passthrough only
- **Isolation:** None (bare metal or hardened Docker)
- **Rationale:** Simplest implementation, maximum performance
- **Risk accepted:** No multi-tenant GPU security
- **Pricing:** Premium tier only ($2-4/hr A100)

**Phase 2 (Growth):**
- **Technology:** Add Kata Containers for GPU isolation
- **Isolation:** VM-level for untrusted GPU workloads
- **Rationale:** Security for untrusted users with GPUs
- **Migration:** New GPU nodes support Kata
- **Pricing:** Isolated GPU +15% vs dedicated

**Phase 3 (Scale):**
- **Technology:** NVIDIA MIG for multi-tenancy
- **Isolation:** Hardware partitioning (7 instances per A100)
- **Rationale:** Higher density, better economics
- **Additional:** H100 with GPU TEE for confidential computing
- **Pricing:** MIG instances at 1/7th dedicated price

**GPU + Confidential Computing:**
- H100 with GPU TEE + AMD SEV-SNP
- Encrypted bounce buffer CPU↔GPU
- Enterprise feature (Phase 3)
- Unlocks: Healthcare ML, financial models, proprietary algorithms

### 4. Network Security: iptables vs Cilium

**Vision A:** Basic isolation (network namespaces, firewalls)
**Vision B:** Cilium + eBPF (identity-based, high-performance)

**Performance Comparison:**

| Metric | iptables | Cilium (eBPF) | Improvement |
|--------|----------|---------------|-------------|
| Throughput | 1 Gbps | 1.5-2 Gbps | 50-100% |
| Latency | 100μs | 50μs | 2x faster |
| Rules | 1,000 limit | 100,000+ | 100x scale |
| Policy type | IP-based | Identity-based | Portable |
| Encryption | IPsec (15% overhead) | WireGuard (5% overhead) | 3x better |

**Cost Analysis:**

**iptables:**
- Cost: $0 (included in Linux)
- Expertise: Common (easy to hire)
- Performance: Sufficient for <1Gbps
- Scalability: Limited to 1,000s of rules

**Cilium:**
- Cost: $50K/year (training, consulting)
- Expertise: Specialized (harder to hire)
- Performance: Required for >1Gbps
- Scalability: 100,000s of workloads

**Synthesis Recommendation:**

**Phase 1 (MVP):**
- Use iptables with network namespaces
- Cost: $0
- Sufficient for: <1,000 concurrent jobs, <1Gbps throughput

**Phase 2 (Growth):**
- Migrate to Cilium
- Trigger: >10,000 concurrent jobs OR >1Gbps network throughput
- Investment: $50K (one-time training)
- ROI: 50-100% throughput improvement, better security

**Phase 3 (Scale):**
- Cilium + Hubble (observability)
- WireGuard encryption for all inter-node traffic
- Network policies for compliance (HIPAA, PCI-DSS)

### 5. Checkpoint/Restart Security

**Vision A:** DMTCP for reliability
**Vision B:** CRIU with security concerns

**Security Analysis:**

**DMTCP:**
- **Capabilities required:** None special (library-level)
- **Attack vectors:**
  - Malicious checkpoint files (code injection)
  - Checkpoint tampering (integrity)
  - Checkpoint inspection (confidentiality)
- **Mitigations:**
  - Checkpoint signing (verify integrity)
  - Checkpoint encryption (protect confidentiality)
  - Sandbox checkpoint restore (limit damage)

**CRIU:**
- **Capabilities required:** SYS_PTRACE, SYS_ADMIN (DANGEROUS)
- **Attack vectors:**
  - Capability abuse (container escape)
  - Checkpoint file manipulation
  - Process injection attacks
- **Mitigations:**
  - Drop capabilities after checkpoint
  - Seccomp filtering during restore
  - Rootless containers (Podman)

**Security Concerns:**

1. **Can malicious checkpoints be crafted?**
   - YES: Checkpoint files contain executable state
   - Attack: Inject malicious code into checkpoint
   - Defense: Cryptographic signing + verification

2. **Should checkpoints be encrypted?**
   - YES for sensitive workloads:
     - Healthcare data (HIPAA)
     - Financial data (PCI-DSS)
     - Proprietary models (IP protection)
   - Encryption: AES-256 with customer-managed keys

3. **How to verify checkpoint integrity?**
   - Digital signatures (Ed25519)
   - Hash verification (SHA-256)
   - Timestamp validation (prevent replay)

**Synthesis Recommendation:**

**For MVP:**
- DMTCP with basic integrity checks
- Checkpoint signing (prevent tampering)
- No encryption (performance overhead)

**For Enterprise:**
- DMTCP with full security
- Checkpoint encryption (AES-256)
- Customer-managed keys (KMS)
- Attestation before restore

---

## Contradiction Resolution

### 1. Confidential Computing: Phase 3 vs Production Feature?

**Vision A:** Phase 3 enterprise feature (12-18 months after MVP)
**Vision B:** Production feature from day one

**Resolution:**
- Vision A is correct for TIMELINE
- Vision B is correct for ARCHITECTURE
- **Synthesis:** Design for confidential computing, implement in Phase 2/3

**Rationale:**
- Architectural decisions (VM-level isolation) enable later SEV-SNP
- Don't implement SEV-SNP for MVP (too expensive, no demand)
- Have clear path to add when enterprise customers demand it
- Design APIs with attestation in mind (future-proof)

**Implementation:**
- Phase 1: No confidential computing (cost/complexity)
- Phase 2: Add for first enterprise customer who demands it (ROI-driven)
- Phase 3: Standard offering for regulated industries

### 2. Container Runtime: Implied vs Specified?

**Vision A:** Doesn't specify (implies Docker/containerd)
**Vision B:** Specifies CRI-O for security

**Resolution:**
- Start with containerd (Vision A implicit)
- Migrate to CRI-O at scale (Vision B aspiration)
- **Synthesis:** Pragmatic evolution

**Rationale:**
- CRI-O's 1-2% security improvement doesn't justify MVP delay
- Containerd has larger ecosystem, faster to implement
- CRI-O makes sense when team has Kubernetes expertise

**Decision:** containerd for Phase 1, CRI-O evaluation in Phase 2

### 3. Network Security: Basic vs Advanced?

**Vision A:** Basic isolation (firewalls, namespaces)
**Vision B:** Cilium + eBPF from day one

**Resolution:**
- Vision A correct for MVP
- Vision B correct for scale
- **Synthesis:** Progressive enhancement

**Migration trigger:** >10,000 concurrent jobs OR >1Gbps throughput

### 4. GPU Isolation: Passthrough vs Kata Containers?

**Vision A:** Passthrough priority (performance)
**Vision B:** Kata Containers (only isolation option)

**Resolution:**
- BOTH are correct for different use cases
- **Synthesis:** Tiered GPU offering

**Tier Structure:**
- Premium: Dedicated passthrough (trusted users, max performance)
- Standard: Kata Containers (untrusted users, isolated)
- Future: MIG for multi-tenancy (Phase 3)

---

## Unified Threat Model Preview

(Full details in `threat-model-comprehensive.md`)

### Adversary Types (from Vision B)

1. **Malicious Tenants**
   - Container escape attempts
   - Resource abuse
   - Network attacks on other tenants

2. **Compromised Providers**
   - Physical hardware access
   - Memory inspection
   - Malicious hypervisor

3. **Network Attackers**
   - Man-in-the-middle attacks
   - Eavesdropping
   - DDoS attacks

4. **Supply Chain Threats**
   - Malicious container images
   - Compromised dependencies
   - Backdoored software

### Vision A Additions

5. **Provider Fraud**
   - Fake GPU specifications
   - Overstated capabilities
   - Resource unavailability after payment

6. **Buyer Fraud**
   - Credit card fraud
   - Account takeover
   - Refund abuse

### Mitigation Priorities

**Phase 1 (MVP):**
1. Container escape (Firecracker for Tier 1)
2. Provider fraud (entry benchmarking)
3. Resource abuse (cgroups, quotas)

**Phase 2 (Growth):**
4. Network attacks (Cilium)
5. Memory inspection (SEV-SNP for enterprise)
6. Supply chain (image scanning)

**Phase 3 (Scale):**
7. Advanced persistent threats
8. Zero-day exploits (bug bounty)
9. Insider threats (audit logs, SIEM)

---

## Next Steps

This research log provides the foundation for six detailed synthesis documents:

1. ✅ **research-log.md** (this document)
2. ⏳ **threat-model-comprehensive.md** - Unified threat analysis
3. ⏳ **isolation-strategy-synthesis.md** - Combined trust + workload isolation
4. ⏳ **confidential-computing-roadmap.md** - When/how to implement SEV-SNP
5. ⏳ **security-by-phase.md** - Phased security implementation
6. ⏳ **security-operations.md** - Testing, compliance, monitoring

---

## Key Takeaways

### Vision A Strengths to Preserve
- Pragmatic phased approach (MVP → Production → Enterprise)
- Trust-based tiering (progressive trust reduces overhead)
- DMTCP checkpoint/restart (competitive advantage)
- Clear timeline and cost estimates

### Vision B Strengths to Integrate
- Comprehensive threat model (4 adversary types)
- Workload-specific isolation (technical constraints)
- Network security detail (Cilium + eBPF)
- Security operations roadmap

### Synthesis Principles
1. **No premature optimization:** Don't over-engineer MVP
2. **Future-proof architecture:** Design for Phase 3, build for Phase 1
3. **Cost-benefit analysis:** Every security layer must justify ROI
4. **Migration triggers:** Clear metrics for when to invest
5. **Risk acceptance:** Explicitly document risks by phase

### Security Philosophy

**The synthesis adopts a "Progressive Security Maturity" model:**

- **MVP:** Minimum viable security (acceptable risk for early adopters)
- **Growth:** Production-grade security (enterprise-ready)
- **Scale:** Defense-in-depth (multiple layers, no single point of failure)

This balances Vision A's pragmatism with Vision B's comprehensiveness, delivering a security architecture that protects users without breaking the budget or delaying launch.

---

**Research completed:** October 14, 2025
**Next document:** `threat-model-comprehensive.md`
