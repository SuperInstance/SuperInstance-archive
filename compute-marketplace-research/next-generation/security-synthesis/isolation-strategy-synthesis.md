# Isolation Strategy Synthesis
## Combined Trust-Based and Workload-Based Isolation Architecture

**Date:** October 14, 2025
**Purpose:** Unified isolation technology selection combining Vision A's trust tiers with Vision B's workload-specific requirements

---

## Executive Summary

This document synthesizes Vision A's **trust-based three-tier model** with Vision B's **workload-specific isolation selection** to create a comprehensive isolation strategy that considers BOTH user trust level AND technical workload requirements.

**Key Innovation:** The synthesis creates a **2-dimensional decision matrix** where isolation technology is determined by the intersection of:
1. **User Trust Level** (Untrusted → Verified → Trusted)
2. **Workload Type** (CPU, GPU, Serverless, Distributed)

This approach resolves the apparent contradiction between the two visions by recognizing that:
- Trust level determines the **minimum security baseline**
- Workload type determines the **technically feasible options**
- Performance requirements determine the **optimal choice within constraints**

**Result:** A flexible, cost-effective isolation architecture that provides maximum security for untrusted workloads while delivering optimal performance for trusted users.

---

## Isolation Technologies Overview

### 1. Firecracker MicroVMs

**Architecture:**
- KVM-based micro Virtual Machine Manager (VMM)
- Written in Rust (50,000 lines vs QEMU's 1.4M)
- Hardware virtualization (requires KVM/VT-x/AMD-V)

**Performance Characteristics:**
| Metric | Value | Comparison |
|--------|-------|------------|
| Startup Time | <100ms (125ms typical) | 100x faster than traditional VM |
| Memory Overhead | <5 MiB per microVM | 90% reduction vs QEMU |
| CPU Overhead | 0-2% | Near-native performance |
| Throughput | 1000s/sec per host | Suitable for serverless |
| Boot to Code | <1 second | AWS Lambda proven |

**Security Model:**
- Each microVM has own kernel (no shared kernel)
- Hardware virtualization provides complete isolation
- Jailer component: seccomp-bpf, cgroups, chroot
- Minimal attack surface: 40 syscalls vs 400+ Linux
- Guest kernel treated as untrusted

**Limitations:**
- Requires bare metal (no nested virtualization)
- Limited device support (by design)
- No GPU passthrough (intentional security choice)
- Higher complexity than containers

**Best For:**
- Untrusted users (new registrations)
- Serverless functions (fast cold start)
- Maximum isolation requirements
- Short-lived workloads (<10 minutes)

**Implementation Complexity:** 8/10
**Timeline:** 6-9 months, 3-4 engineers

---

### 2. gVisor Sandboxing

**Architecture:**
- User-space kernel written in memory-safe Go
- Syscall interception and emulation
- Application kernel isolation (not hardware VM)

**Performance Characteristics:**
| Metric | CPU Workload | I/O Workload | Network Workload |
|--------|--------------|--------------|------------------|
| Overhead | 3-10% | 15-30% | 20-40% |
| Best Case | API servers, batch | - | - |
| Worst Case | - | Databases | Load balancers |
| Startup | ~seconds | ~seconds | ~seconds |
| Memory | +50-100MB Sentry | +50-100MB | +50-100MB |

**Security Model:**
- Reduced host kernel exposure (<20 syscalls)
- Protects against kernel CVEs
- Defense against container escape (e.g., CVE-2025-23266)
- Each app gets isolated kernel implementation

**GPU Support:**
- nvproxy: NVIDIA GPU driver proxy
- Suitable for inference (not multi-tenant)
- ~10-15% overhead for GPU operations
- No MIG support (driver proxy limitations)

**Limitations:**
- Performance penalty for I/O
- Not suitable for databases
- Higher memory overhead
- Some application compatibility issues

**Best For:**
- Verified users (established reputation)
- CPU-intensive workloads
- ML inference (non-critical performance)
- Workloads tolerating 10-20% overhead

**Implementation Complexity:** 6/10
**Timeline:** Integrated with Firecracker (6-9 months)

---

### 3. Kata Containers

**Architecture:**
- Full VM technology with lightweight VMs
- Can use QEMU or Firecracker as hypervisor
- Kubernetes-compatible via CRI

**Performance Characteristics:**
| Metric | Value | Notes |
|--------|-------|-------|
| Startup Time | 150-300ms | Slower than Firecracker due to full VM |
| CPU Performance | Near-native | Identical to Firecracker/runC |
| Boot to Code | 2-5 seconds | Including Kubernetes pod init |
| Memory | ~100MB per pod | Higher than Firecracker |

**Critical Feature: GPU Passthrough**
- **ONLY isolation technology supporting GPU with VM-level security**
- Supports NVIDIA PCI passthrough
- Compatible with CUDA workloads
- Enables secure multi-tenant GPU

**Security Model:**
- VM-level isolation (same as Firecracker)
- Can use Firecracker as VMM (combines benefits)
- Better device support than pure Firecracker
- Hardware virtualization boundary

**Limitations:**
- Slower startup than Firecracker
- Higher memory overhead
- Kubernetes dependency (CRI integration)
- More complex than gVisor

**Best For:**
- **GPU workloads requiring isolation**
- Multi-tenant GPU environments
- Kubernetes deployments
- Workloads needing device support

**Implementation Complexity:** 7/10
**Timeline:** 4-6 months (if Firecracker already done)

---

### 4. Hardened Docker Containers

**Architecture:**
- Standard OCI containers with security hardening
- Namespace and cgroup isolation
- Shared kernel with host

**Performance Characteristics:**
| Metric | Value | Advantage |
|--------|-------|-----------|
| Overhead | 1-3% | Best performance |
| Startup | Instant (<1s) | Fastest option |
| Memory | Minimal | No VM overhead |
| Compatibility | 100% | Standard OCI |

**Security Hardening:**
- Read-only root filesystem
- Dropped capabilities (CAP_SYS_ADMIN, etc.)
- Seccomp profiles (whitelist syscalls)
- AppArmor/SELinux mandatory access control
- No new privileges flag
- Network isolation (namespaces)

**Security Limitations:**
- **Shared kernel** (vulnerable to CVE-2025-9074, etc.)
- Container escape possible (recent critical CVEs)
- Requires trust in user not to exploit

**Resource Limits:**
- cgroups: CPU, memory, PIDs, I/O
- Network: bandwidth, connection limits
- Storage: disk quotas, IOPS limits

**Best For:**
- Trusted organizations (long-term customers)
- High-volume users (>100 jobs)
- Performance-critical workloads
- Internal/proprietary code

**Implementation Complexity:** 3/10
**Status:** Already implemented (4,000+ lines production code)

---

## Trust-Based Tiering (Vision A)

### Tier 1: Untrusted Users

**Criteria:**
- New users (< 10 successful jobs)
- No payment history
- New account (< 30 days)
- Anonymous users
- Flagged by fraud detection

**Isolation Requirements:**
- **Maximum isolation** (hardware virtualization)
- Container escape prevention (critical)
- Memory inspection resistance (optional for sensitive workloads)
- Network isolation (mandatory)

**Technology Options:**
- Firecracker microVMs (default for CPU/serverless)
- Kata Containers (required for GPU)

**Rationale:**
- Zero trust assumption
- Protect platform from malicious users
- Protect other users from cross-tenant attacks
- Accept 0-15% performance overhead for security

**Pricing Premium:** +10-15% (isolation cost)

---

### Tier 2: Verified Users

**Criteria:**
- 10-99 successful jobs
- >90% completion rate
- Payment history ($100+)
- Account age >30 days
- No fraud flags

**Isolation Requirements:**
- **Balanced isolation** (syscall filtering)
- Kernel CVE protection
- Container escape mitigation
- Acceptable performance trade-off (10-20% overhead)

**Technology Options:**
- gVisor (default for CPU)
- Kata Containers (for GPU)
- Docker (opt-in downgrade for trusted workloads)

**Rationale:**
- Established reputation
- Economic incentive to behave (sunk cost)
- Unlikely to attack platform
- Performance matters more than for Tier 1

**Pricing Premium:** +5% (gVisor overhead)

---

### Tier 3: Trusted Organizations

**Criteria:**
- 100+ successful jobs
- >95% completion rate
- Contract relationship
- $10K+ lifetime spend
- Background check completed
- Enterprise agreement

**Isolation Requirements:**
- **Minimal isolation** (performance priority)
- Acceptable risk (shared kernel)
- Trust-based security model
- Fastest performance (1-3% overhead)

**Technology Options:**
- Hardened Docker (default)
- gVisor (opt-in for extra security)
- Firecracker (opt-in for maximum isolation)

**Rationale:**
- Established business relationship
- Financial stake in platform success
- Reputation risk prevents abuse
- Performance critical for production workloads

**Pricing:** Baseline (no premium)

---

## Workload-Based Selection (Vision B)

### CPU-Intensive Workloads

**Characteristics:**
- Batch processing
- Data pipelines
- ML training (CPU-only)
- Scientific computing
- Video encoding (CPU)

**Performance Requirements:**
- CPU cycles (maximize utilization)
- Memory bandwidth
- Minimal I/O
- Low network usage

**Isolation Options:**

| User Tier | Default | Alternative | Opt-In |
|-----------|---------|-------------|--------|
| Untrusted | Firecracker | - | - |
| Verified | gVisor | Docker (downgrade) | Firecracker (upgrade) |
| Trusted | Docker | gVisor (upgrade) | Firecracker (max security) |

**Performance Impact:**
- Firecracker: 0-2% overhead (best isolation)
- gVisor: 3-10% overhead (balanced)
- Docker: 1-3% overhead (minimal)

**Recommendation:**
- Default to trust-tier isolation
- Allow performance-sensitive users to downgrade (with consent)
- Allow privacy-conscious users to upgrade (with premium)

---

### GPU Workloads

**Characteristics:**
- ML training (deep learning)
- ML inference (production models)
- Rendering (graphics, video)
- Scientific computing (CUDA)
- Cryptocurrency (blocked)

**Performance Requirements:**
- GPU compute (CUDA cores, tensor cores)
- GPU memory bandwidth
- CPU-GPU transfer (PCIe)
- Multi-GPU networking (NCCL)

**Technical Constraint:**
**Kata Containers is the ONLY isolation technology supporting GPU passthrough with VM-level security**

**Isolation Matrix:**

| User Tier | Sensitive Data | Standard Workload | Performance-Critical |
|-----------|----------------|-------------------|----------------------|
| Untrusted | Kata + SEV-SNP (Phase 3) | Kata Containers | Kata Containers |
| Verified | Kata Containers | Kata or Passthrough (user choice) | Passthrough |
| Trusted | Kata (upgrade) | Passthrough | Passthrough + MIG (Phase 3) |

**GPU Security Considerations:**

1. **Dedicated Passthrough (No Isolation)**
   - Security: Provider can inspect GPU memory
   - Performance: 98-100% native
   - Cost: Lowest (no overhead)
   - Best for: Trusted users, non-sensitive data

2. **Kata Containers (VM Isolation)**
   - Security: Hardware virtualization, provider cannot access VM GPU memory
   - Performance: 95-98% (minimal overhead)
   - Cost: +15% (isolation implementation)
   - Best for: Untrusted users, sensitive data

3. **NVIDIA MIG (Hardware Partitioning) - Phase 3**
   - Security: Hardware-level isolation (7 instances per A100)
   - Performance: 85-95% (partitioning overhead)
   - Cost: Better density (7x tenants per GPU)
   - Best for: Multi-tenant efficiency at scale

4. **H100 + SEV-SNP (Confidential Computing) - Phase 3**
   - Security: GPU memory encrypted, provider cannot inspect
   - Performance: 90-95% (encryption overhead)
   - Cost: Premium hardware ($30K+ per GPU)
   - Best for: Healthcare, finance, proprietary models

**Recommendation:**
- Phase 1: Passthrough only (simplest)
- Phase 2: Add Kata for untrusted GPU users
- Phase 3: Add MIG for density, H100+SEV-SNP for enterprise

---

### Serverless Functions

**Characteristics:**
- Short-lived (<10 minutes)
- Event-driven triggers
- Stateless execution
- Frequent cold starts
- High concurrency

**Performance Requirements:**
- **Fast cold start** (<1 second critical)
- Minimal memory overhead
- Instant shutdown
- High density (1000s per host)

**Technical Constraint:**
**Firecracker is the ONLY option for sub-second cold starts at scale**

**Isolation Decision:**

| User Tier | Technology | Rationale |
|-----------|----------|-----------|
| Untrusted | Firecracker | Required (fast + secure) |
| Verified | Firecracker | Required (fast + secure) |
| Trusted | Firecracker OR Docker | Firecracker preferred, Docker for long-lived "serverless" |

**Rationale:**
- Sub-100ms boot time is table stakes (RunPod: <15s is competition)
- gVisor too slow (~seconds startup)
- Docker lacks isolation for serverless (shared kernel risk)
- Kata slower than Firecracker (150-300ms)

**Special Case: Long-Running "Serverless"**
- If "serverless" job runs >1 hour, startup time less critical
- Trusted users can use Docker for better compatibility
- Untrusted users still require Firecracker (security > compatibility)

---

### Distributed Multi-Node Workloads

**Characteristics:**
- MPI (Message Passing Interface)
- Multi-GPU training (NCCL)
- Spark/Hadoop clusters
- Distributed rendering

**Performance Requirements:**
- Low-latency networking (RDMA, InfiniBand)
- Node-to-node trust (shared memory, MPI)
- Checkpoint/restart support (DMTCP)
- Gang scheduling (all nodes start together)

**Isolation Challenges:**
- **MPI requires shared memory** (limits isolation)
- **NCCL requires GPU-Direct RDMA** (P2P GPU access)
- **Checkpoint/restart complexity** (coordinated across nodes)

**Isolation Decision:**

| User Tier | Technology | Rationale |
|-----------|----------|-----------|
| Untrusted | Kata Containers (if GPU) or Firecracker (CPU-only) | VM isolation per node, encrypted inter-node |
| Verified | gVisor OR Docker | MPI compatibility matters |
| Trusted | Docker | Maximum performance, MPI support |

**Network Security:**
- **Untrusted:** WireGuard encrypted tunnels between nodes (<5% overhead)
- **Verified:** TLS/mTLS for control plane, plaintext data plane (performance)
- **Trusted:** Plaintext (trust + performance)

**DMTCP Compatibility:**
- Works with Docker, gVisor, Firecracker
- Requires shared checkpoint storage (S3-compatible)
- Coordinated checkpoint across nodes
- <4 second restart time (64-node computation)

---

## Combined Decision Matrix

### 2D Isolation Selection Framework

```
                CPU Workload          GPU Workload           Serverless            Distributed MPI
              ┌──────────────────┬──────────────────┬──────────────────┬──────────────────────┐
Untrusted     │ Firecracker      │ Kata Containers  │ Firecracker      │ Firecracker + WG     │
  (Tier 1)    │ (0-2% overhead)  │ (15% overhead)   │ (required)       │ (encrypted inter-node)│
              │ Required         │ ONLY option      │ Fast boot        │ VM per node          │
              ├──────────────────┼──────────────────┼──────────────────┼──────────────────────┤
Verified      │ gVisor (default) │ Kata OR          │ Firecracker      │ gVisor OR Docker     │
  (Tier 2)    │ (10% overhead)   │ Passthrough*     │ (preferred)      │ (MPI compat)         │
              │ OR Docker (opt)  │ (user choice)    │ Docker (long)    │ TLS control plane    │
              ├──────────────────┼──────────────────┼──────────────────┼──────────────────────┤
Trusted       │ Docker (default) │ Passthrough      │ Firecracker OR   │ Docker               │
  (Tier 3)    │ (3% overhead)    │ (98-100% perf)   │ Docker (long)    │ (max performance)    │
              │ gVisor (opt)     │ Kata (opt)       │ User choice      │ RDMA/InfiniBand      │
              └──────────────────┴──────────────────┴──────────────────┴──────────────────────┘

* Passthrough = Bare metal GPU passthrough (no isolation, maximum performance)
  WG = WireGuard encrypted tunnels
```

### Decision Logic (Programmatic)

```python
def select_isolation_technology(user_tier, workload_type, user_preference=None):
    """
    Select isolation technology based on user trust tier and workload type.

    Args:
        user_tier: "untrusted" | "verified" | "trusted"
        workload_type: "cpu" | "gpu" | "serverless" | "distributed"
        user_preference: "upgrade" | "downgrade" | None (override default)

    Returns:
        isolation_tech: "firecracker" | "gvisor" | "kata" | "docker"
    """

    # Serverless ALWAYS requires Firecracker (fast boot)
    if workload_type == "serverless":
        return "firecracker"  # Exception for long-running trusted: docker

    # GPU workloads with isolation REQUIRE Kata (only option)
    if workload_type == "gpu":
        if user_tier == "untrusted":
            return "kata"  # Only isolation option for GPU
        elif user_tier == "verified":
            # User choice: isolation (kata) vs performance (passthrough)
            return user_preference or "kata"  # Default kata (safer)
        else:  # trusted
            # Default passthrough, opt-in kata
            return user_preference or "passthrough"

    # CPU workloads: trust-tier determines default
    if workload_type == "cpu" or workload_type == "distributed":
        if user_tier == "untrusted":
            return "firecracker"  # Maximum isolation
        elif user_tier == "verified":
            if user_preference == "downgrade":
                return "docker"  # Performance downgrade (user consent)
            elif user_preference == "upgrade":
                return "firecracker"  # Security upgrade (user pays premium)
            else:
                return "gvisor"  # Default balanced
        else:  # trusted
            if user_preference == "upgrade":
                return "gvisor"  # Opt-in security
            else:
                return "docker"  # Default performance

    raise ValueError(f"Unknown workload type: {workload_type}")


# Example usage:
select_isolation_technology("untrusted", "gpu")
# Returns: "kata" (forced by technical constraint)

select_isolation_technology("verified", "cpu", "downgrade")
# Returns: "docker" (user accepts risk for performance)

select_isolation_technology("trusted", "gpu", "upgrade")
# Returns: "kata" (user pays premium for isolation despite trust)
```

---

## Performance Overhead Analysis

### CPU Workloads

| Technology | Best Case | Typical | Worst Case | Scenario |
|-----------|-----------|---------|------------|----------|
| Firecracker | 0% | 2% | 5% | CPU-intensive batch |
| gVisor | 3% | 10% | 30% | I/O-heavy (worst for databases) |
| Kata Containers | 0% | 2% | 5% | Similar to Firecracker |
| Docker | 1% | 2% | 3% | Minimal overhead |

**Recommendation:**
- Firecracker optimal for CPU-intensive
- Avoid gVisor for I/O workloads
- Docker best performance for trusted

---

### GPU Workloads

| Technology | Training | Inference | Rendering | Notes |
|-----------|----------|-----------|-----------|-------|
| Kata Containers | 95-98% | 96-99% | 97-99% | VM overhead minimal for GPU |
| Passthrough (no isolation) | 98-100% | 99-100% | 99-100% | Baseline performance |
| NVIDIA MIG (Phase 3) | 85-95% | 90-97% | 88-95% | Hardware partitioning overhead |
| H100 + SEV-SNP (Phase 3) | 90-95% | 93-97% | N/A | Encryption overhead |

**Key Insight:** Kata Containers has minimal GPU overhead (2-5%) because GPU compute dominates CPU overhead

**Recommendation:**
- Kata acceptable for most GPU workloads
- Passthrough for performance-critical (trusted users only)
- MIG for Phase 3 density optimization

---

### Serverless Functions

| Technology | Cold Start | Memory Overhead | Density |
|-----------|------------|-----------------|---------|
| Firecracker | <100ms | 5 MiB | 1000s per host |
| gVisor | ~seconds | 50-100 MiB | 100s per host |
| Kata | 150-300ms | 100 MiB | 100s per host |
| Docker | <1s | Minimal | 1000s per host |

**Critical Metric: Cold Start**
- RunPod competition: <15 seconds
- AWS Lambda: <100ms with Firecracker
- Marketplace target: <1 second

**Recommendation:**
- Firecracker ONLY option for competitive serverless
- Docker acceptable for long-running "serverless" (>1 hour)

---

### Distributed Workloads

**Network Overhead:**

| Security Layer | Latency | Throughput | Overhead |
|---------------|---------|------------|----------|
| None (plaintext) | Baseline | Baseline | 0% |
| TLS 1.3 | +50-100μs | -2-5% | ~3% |
| WireGuard | +20-50μs | -2-5% | ~3% |
| IPsec | +100-200μs | -10-20% | ~15% |

**Recommendation:**
- Untrusted: WireGuard (<5% overhead, good security)
- Verified: TLS for control, plaintext for data (performance)
- Trusted: Plaintext (trust + performance)

**DMTCP Overhead:**
- Runtime: <1%
- Checkpoint: 2-30 seconds (depending on memory size)
- Restart: <4 seconds (even 64-node)
- Storage: 2-3x compression with gzip

---

## Network Security Architecture

### Layer 3/4 Isolation (Network Namespaces)

**Technology:** Linux network namespaces + iptables
**Suitable for:** MVP (Phase 1)

**Configuration:**
```bash
# Each job gets isolated network namespace
ip netns add job-<job-id>

# iptables rules (default deny)
iptables -P FORWARD DROP
iptables -P INPUT DROP
iptables -P OUTPUT DROP

# Allow specific egress (e.g., S3, API endpoints)
iptables -A OUTPUT -d <platform-api> -j ACCEPT
iptables -A OUTPUT -d s3.amazonaws.com -j ACCEPT
```

**Pros:**
- Simple, well-understood
- Zero cost (built-in Linux)
- Sufficient for <1,000 concurrent jobs

**Cons:**
- IP-based policies (fragile)
- Doesn't scale >1,000s of rules
- No identity-based security
- Limited observability

**Performance:** Negligible overhead

---

### Layer 7 Policy Enforcement (Cilium + eBPF)

**Technology:** Cilium with eBPF network policies
**Suitable for:** Production (Phase 2)

**Configuration:**
```yaml
# Cilium NetworkPolicy: Identity-based isolation
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: tenant-isolation
spec:
  endpointSelector:
    matchLabels:
      tenant: <tenant-id>
  egress:
  - toEndpoints:
    - matchLabels:
        tenant: <tenant-id>  # Only same tenant
  - toFQDNs:
    - matchPattern: "*.s3.amazonaws.com"  # Allow S3
    - matchPattern: "api.platform.com"    # Allow platform API
  - toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

**Pros:**
- Identity-based (portable across IPs)
- 50-100% throughput improvement vs iptables
- FQDN-based egress filtering
- L7 policy (HTTP/gRPC protocol-aware)
- Rich observability (Hubble)

**Cons:**
- Requires eBPF kernel support (4.9.17+)
- Learning curve (eBPF programming)
- $50K investment (training, expertise)

**Performance:**
- Throughput: +50-100% vs iptables
- Latency: <1ms overhead
- Scales to 100,000+ pods

**Migration Trigger:**
- >10,000 concurrent jobs OR
- >1 Gbps network throughput OR
- Enterprise security requirements (FQDN filtering)

---

### Encryption (WireGuard vs TLS vs IPsec)

**Performance Comparison:**

| Protocol | Overhead | Setup | Use Case |
|----------|----------|-------|----------|
| WireGuard | <5% | Simple | Node-to-node tunnels |
| TLS 1.3 | 2-5% | Moderate | API, service-to-service |
| IPsec | 10-20% | Complex | Legacy VPN |

**Recommendation:**
- **WireGuard:** Inter-node data plane (distributed jobs)
- **TLS 1.3:** Control plane (APIs, orchestration)
- **mTLS:** Service mesh (Linkerd, Istio)

**Configuration (WireGuard):**
```bash
# Generate keys
wg genkey | tee privatekey | wg pubkey > publickey

# Configure interface
ip link add dev wg0 type wireguard
ip address add <node-ip>/24 dev wg0
wg set wg0 private-key privatekey
wg set wg0 listen-port 51820
wg set wg0 peer <peer-pubkey> allowed-ips <peer-ip>/32 endpoint <peer-endpoint>:51820

# Enable
ip link set wg0 up
```

**Performance:** <5% overhead for 1Gbps traffic

---

## GPU Security Deep Dive

### Problem Statement

**GPU security challenge:**
- GPU memory ALWAYS visible to provider (unless H100 + SEV-SNP)
- Multi-tenant GPUs share memory space
- NVIDIA drivers ~20MB of code (large attack surface)
- CUDA allows direct memory access

**Threat Scenarios:**
1. Provider inspects GPU memory (steal ML models)
2. Tenant A accesses Tenant B's GPU memory (shared GPU)
3. Malicious CUDA code exploits driver vulnerability
4. GPU driver bug allows kernel escalation

### Isolation Options (Detailed)

#### 1. No Isolation (Bare Metal Passthrough)

**Configuration:**
```bash
# Bind GPU to VFIO for passthrough
echo "10de 2204" > /sys/bus/pci/drivers/vfio-pci/new_id  # RTX 4090
echo "0000:01:00.0" > /sys/bus/pci/devices/0000:01:00.0/driver/unbind
echo "0000:01:00.0" > /sys/bus/pci/drivers/vfio-pci/bind

# Assign to container/VM
docker run --gpus all --device /dev/nvidia0 <image>
```

**Security:**
- Provider can inspect GPU memory (full visibility)
- No multi-tenant isolation (one job per GPU)
- Host driver compromise affects all jobs

**Performance:** 98-100% native

**Cost:** $2-4/hr A100 (dedicated)

**Best for:** Trusted users, non-sensitive data

---

#### 2. Kata Containers (VM-Level GPU Isolation)

**Configuration:**
```yaml
# Kata Containers with GPU passthrough
apiVersion: v1
kind: Pod
metadata:
  name: gpu-job
spec:
  runtimeClassName: kata-containers
  containers:
  - name: gpu-workload
    image: nvidia/cuda:11.8
    resources:
      limits:
        nvidia.com/gpu: 1
```

**Security:**
- VM isolation protects from provider host access
- Guest kernel vulnerability doesn't affect host
- Provider cannot inspect VM memory (without SEV-SNP)
- Multi-tenant with VM boundaries

**Performance:** 95-98% (2-5% VM overhead)

**Cost:** $2.30-4.60/hr A100 (+15% isolation overhead)

**Best for:** Untrusted users, sensitive data (pre-SEV-SNP)

---

#### 3. NVIDIA MIG (Multi-Instance GPU) - Phase 3

**Configuration:**
```bash
# Enable MIG mode (requires reboot)
nvidia-smi -mig 1

# Create 7 instances (1g.5gb profile on A100)
nvidia-smi mig -cgi 19,19,19,19,19,19,19 -C

# Verify instances
nvidia-smi mig -lgi
```

**Security:**
- Hardware partitioning (7 isolated instances per A100)
- Each instance has own memory space (not accessible to others)
- Quality of Service guarantees
- Better isolation than time-slicing

**Performance:** 85-95% (partitioning overhead)

**Cost:** $0.35-0.65/hr per instance (1/7th of A100)

**Density:** 7x tenants per GPU

**Best for:** Multi-tenant efficiency, Phase 3 optimization

**Hardware:** Ampere+ (A100, H100), not RTX/older

---

#### 4. H100 + AMD SEV-SNP (Confidential Computing) - Phase 3

**Configuration:**
```bash
# Launch VM with SEV-SNP
qemu-system-x86_64 \
  -machine q35,confidential-guest-support=sev0 \
  -object sev-snp-guest,id=sev0,cbitpos=51,reduced-phys-bits=1 \
  -cpu EPYC-v4 \
  -device vfio-pci,host=0000:01:00.0  # H100 GPU
```

**Security:**
- VM memory encrypted (provider cannot inspect)
- GPU memory encrypted via bounce buffer (CPU↔GPU)
- Hardware attestation (verify platform integrity)
- Protects from malicious hypervisor

**Performance:** 90-95% (encryption overhead)

**Cost:** $8-12/hr H100 (premium hardware + encryption overhead)

**Best for:** Healthcare (HIPAA), finance (PCI-DSS), proprietary ML models

**Hardware:** H100 + AMD EPYC (Milan or newer)

---

### GPU Memory Security Best Practices

**For All GPU Workloads:**

1. **Memory Clearing Between Jobs**
```bash
# Zero GPU memory after job completion
nvidia-smi -r  # Reset GPU (clears memory)
```

2. **Memory Limits**
```yaml
resources:
  limits:
    nvidia.com/gpu: 1
    memory: "16Gi"  # Limit addressable memory
```

3. **CUDA Driver Updates**
- Regular driver updates (monthly)
- Subscribe to NVIDIA security advisories
- Test in staging before production

4. **Access Control**
```bash
# Restrict GPU device access
chmod 600 /dev/nvidia0
chown <job-user>:<job-group> /dev/nvidia0
```

**For Multi-Tenant GPUs (MIG):**

5. **Instance Isolation Verification**
```bash
# Verify instance cannot access other instance memory
nvidia-smi mig -lgi  # List instances
# Attempt cross-instance memory access (should fail)
```

6. **QoS Monitoring**
- Monitor guaranteed vs actual performance
- Alert on QoS violations (indicates interference)

---

## Cilium Network Policies (Production Examples)

### Example 1: Tenant Isolation (Default Deny)

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: default-deny-all
spec:
  endpointSelector: {}
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system  # Allow K8s system
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system  # Allow K8s system
  - toFQDNs:
    - matchPattern: "*.svc.cluster.local"  # Allow in-cluster DNS
```

**Effect:** Deny all traffic except Kubernetes system and in-cluster DNS

---

### Example 2: Per-Tenant Allow List

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: tenant-{{ tenant_id }}-egress
spec:
  endpointSelector:
    matchLabels:
      tenant: {{ tenant_id }}
  egress:
  # Allow S3 access
  - toFQDNs:
    - matchPattern: "*.s3.amazonaws.com"
    - matchPattern: "*.s3-{{ region }}.amazonaws.com"
  # Allow platform API
  - toFQDNs:
    - matchName: "api.platform.com"
  # Allow public datasets (e.g., HuggingFace)
  - toFQDNs:
    - matchPattern: "*.huggingface.co"
  # Allow PyPI for package installation
  - toFQDNs:
    - matchPattern: "*.pypi.org"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
  # Deny all other egress
  denyFQDNs:
  - matchPattern: "*"
```

**Effect:** Tenant can only access approved external services

---

### Example 3: Block Cryptocurrency Mining

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: block-mining-pools
spec:
  endpointSelector: {}
  egress:
  # Block common mining pool ports
  - toPorts:
    - ports:
      - port: "3333"  # Stratum
      - port: "4444"  # Stratum
      - port: "8332"  # Bitcoin RPC
      - port: "8333"  # Bitcoin P2P
    action: DENY
  # Block mining pool domains
  - toFQDNs:
    - matchPattern: "*.pool.minergate.com"
    - matchPattern: "*.nanopool.org"
    - matchPattern: "*.ethermine.org"
    - matchPattern: "*.nicehash.com"
    action: DENY
```

**Effect:** Prevent cryptocurrency mining

---

### Example 4: L7 HTTP Policy (Prevent Data Exfiltration)

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: http-egress-filtering
spec:
  endpointSelector:
    matchLabels:
      tenant: {{ tenant_id }}
  egress:
  - toFQDNs:
    - matchPattern: "*.s3.amazonaws.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
      rules:
        http:
        - method: "GET"  # Allow downloads
        - method: "PUT"  # Allow uploads (results)
          headers:
          - "Content-Type: application/octet-stream"
        # DENY all other HTTP methods (POST, DELETE, etc.)
```

**Effect:** Allow only GET/PUT to S3, prevent API abuse

---

## Migration Strategy

### Phase 1 → Phase 2 Migration

**Trigger Conditions:**
- >10,000 concurrent jobs
- >$1M monthly GMV
- First enterprise customer requiring isolation
- Security audit recommends Firecracker

**Migration Steps:**

**Month 1-2: Planning**
1. Firecracker architecture design
2. Hire 3-4 systems engineers (Rust, KVM)
3. Set up bare metal test infrastructure
4. Security audit of Tier 3 (Docker) isolation

**Month 3-5: Implementation**
5. Firecracker microVM integration
6. gVisor integration (parallel track)
7. Automated tier assignment (reputation-based)
8. Testing and benchmarking

**Month 6-7: Gradual Rollout**
9. Week 1: New users only (Tier 1)
10. Week 2: 10% of verified users (Tier 2)
11. Week 3: 50% of verified users
12. Week 4: 100% rollout

**Month 8-9: Optimization**
13. Performance tuning
14. Cost optimization
15. User feedback incorporation

**Rollback Plan:**
- Keep Docker infrastructure running
- Feature flag for rollback
- Gradual migration (not big-bang)

---

### Phase 2 → Phase 3 Migration

**Trigger Conditions:**
- >100,000 concurrent jobs
- First healthcare/finance customer (HIPAA/PCI-DSS)
- >$10M monthly GMV
- Competitive pressure (others offering confidential computing)

**Migration Steps:**

**Month 1-3: Hardware Acquisition**
1. Purchase AMD EPYC servers (SEV-SNP support)
2. Purchase H100 GPUs (GPU TEE support)
3. Deploy in new regions (avoid disrupting existing)

**Month 4-9: Implementation**
4. AMD SEV-SNP integration
5. H100 GPU TEE integration
6. Attestation service (Intel Trust Authority or self-hosted)
7. Key management system (customer-managed keys)

**Month 10-12: Pilot**
8. Beta test with first enterprise customer
9. Compliance certification (HIPAA, PCI-DSS)
10. Security audit (third-party)

**Month 13-18: General Availability**
11. Gradual rollout to all regions
12. Marketing and positioning
13. Enterprise sales enablement

**Pricing:**
- SEV-SNP: 2-3x premium vs standard
- H100 + GPU TEE: 4-5x premium vs standard GPU

---

## Cost Analysis

### Total Cost of Ownership (3 Years)

**Phase 1 (MVP):**
- Infrastructure: $50K (Docker hardening refinement)
- Engineering: $150K (2 engineers × 3 months)
- **Total:** $200K

**Phase 2 (Production):**
- Infrastructure: $500K (bare metal servers, networking)
- Engineering: $800K (7 engineers × 6 months)
- Cilium expertise: $50K (training, consulting)
- **Total:** $1.35M

**Phase 3 (Enterprise):**
- Infrastructure: $1M (AMD EPYC, H100 GPUs)
- Engineering: $600K (5 engineers × 6 months)
- Compliance: $200K (SOC 2, HIPAA, PCI-DSS)
- **Total:** $1.8M

**Grand Total (3 Years):** $3.35M

---

### Per-Job Cost Breakdown

**Assumptions:**
- 100,000 jobs/month at scale
- Average job duration: 3 hours
- Average job value: $10 (revenue to platform)

**Cost per Job:**

| Component | Tier 1 (Firecracker) | Tier 2 (gVisor) | Tier 3 (Docker) |
|-----------|---------------------|----------------|----------------|
| Compute overhead | $0.20 (2%) | $1.00 (10%) | $0.30 (3%) |
| Network overhead | $0.05 | $0.05 | $0.05 |
| Storage overhead | $0.02 | $0.02 | $0.02 |
| Orchestration | $0.10 | $0.10 | $0.10 |
| **Total overhead** | **$0.37** | **$1.17** | **$0.47** |
| **As % of $10 job** | **3.7%** | **11.7%** | **4.7%** |

**Gross Margin Analysis:**
- Platform commission: $1.00 (10% of $10 job)
- Tier 1 overhead: $0.37 → Net: $0.63 (63% margin)
- Tier 2 overhead: $1.17 → Net: -$0.17 (LOSS!)
- Tier 3 overhead: $0.47 → Net: $0.53 (53% margin)

**Insight:** gVisor (Tier 2) has negative margins for low-value jobs. Solutions:
1. Higher commission for Tier 2 (11% vs 10%)
2. Price premium for isolation (+5%)
3. Tier 2 users auto-upgrade to Tier 3 faster (reduce gVisor usage)

---

## Success Metrics

### Security Metrics

**Phase 1 (MVP):**
- Container escapes: 0 successful (from Tier 3 Docker)
- Provider fraud detection rate: <1%
- Job completion rate: >99%

**Phase 2 (Production):**
- Container escapes: 0 successful (all tiers)
- Cross-tenant network access: 0 successful
- Malicious image detection rate: >95%
- Provider fraud detection rate: <0.1%

**Phase 3 (Enterprise):**
- Confidential computing adoption: >10% of GPU revenue
- Compliance certifications: SOC 2, HIPAA, PCI-DSS
- Enterprise customer satisfaction: >90%

### Performance Metrics

**Phase 1:**
- Docker overhead: <3%
- Job startup time: <10 seconds

**Phase 2:**
- Firecracker cold start: <100ms
- gVisor CPU overhead: <15%
- Cilium network throughput: >1Gbps per node

**Phase 3:**
- SEV-SNP overhead: <10%
- H100 GPU TEE overhead: <10%
- MIG utilization: >80% (7 tenants per GPU)

### Business Metrics

**Phase 1:**
- Break-even: $2-3M monthly GMV
- Gross margin: >50%

**Phase 2:**
- Enterprise customer acquisition: >5 customers
- GMV growth: >50% QoQ
- Tier 1 usage: >50% of new users

**Phase 3:**
- Confidential computing revenue: >$10M/year
- Enterprise market share: >10%
- Premium pricing realization: 2-3x standard

---

## Conclusion

This isolation strategy synthesis successfully combines Vision A's pragmatic trust-based tiering with Vision B's workload-specific technology selection to create a flexible, cost-effective security architecture.

**Key Principles:**
1. **Trust tier determines minimum security baseline**
2. **Workload type determines technically feasible options**
3. **User preference allows upgrades/downgrades (with consent)**
4. **Performance and cost guide optimal selection**

**Critical Success Factors:**
- Firecracker for Tier 1 (non-negotiable for untrusted CPU/serverless)
- Kata Containers for GPU isolation (ONLY option with VM-level security)
- Cilium for Phase 2+ network security (identity-based, scalable)
- SEV-SNP for Phase 3 enterprise (memory inspection prevention)

**Result:** A security architecture that protects users without breaking the budget, enables enterprise market entry, and delivers competitive performance.

---

**Next Document:** `confidential-computing-roadmap.md` (detailed SEV-SNP implementation plan and ROI analysis)
