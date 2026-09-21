# Decision Framework: When to Choose Vision A vs Vision B Components

**Quick Reference Guide for Technology Migrations**

**Version:** 1.0
**Date:** October 14, 2025
**Purpose:** Rapid decision making for architecture choices

---

## How to Use This Framework

For each technology decision:
1. Check current metrics against triggers
2. If triggers are NOT met → Stay with Vision A (simpler, cheaper)
3. If triggers ARE met → Migrate to Vision B (production-grade)
4. If unsure → Stay with Vision A (avoid premature optimization)

**Golden Rule:** When in doubt, don't migrate. Vision A is sufficient until metrics prove otherwise.

---

## Quick Decision Matrix

| Component | Vision A (Start) | Vision B (Migrate) | Migration Trigger | Typical Timeline |
|-----------|-----------------|-------------------|-------------------|------------------|
| **Orchestration** | K3s | Nomad | Heterogeneous workloads needed | Month 18-24 (if ever) |
| **Database (Jobs)** | PostgreSQL | TiDB | >50K writes/sec OR >5 shards | Month 18-24 |
| **Database (Financial)** | CockroachDB | CockroachDB | Use from day 1 | Month 1 |
| **Cache** | Valkey | Redis Enterprise | Multi-region active-active | Month 22-30 |
| **Messaging** | NATS | NATS + Kafka | Audit replay OR >1M events/sec | Month 19-24 |
| **Search** | Meilisearch | Meilisearch | No migration needed | N/A |
| **Monitoring** | Prometheus | VictoriaMetrics | >8M active time series | Month 18-24 |
| **Logging** | Loki | Loki | No migration needed | N/A |
| **Tracing** | Tempo | Tempo | No migration needed | N/A |
| **Security Tier 1** | Docker | gVisor | Untrusted workloads | Month 6-9 |
| **Security Tier 2** | - | Firecracker | Enterprise isolation | Month 18-24 |
| **Security Tier 3** | - | SEV-SNP | Confidential computing | Month 25+ |
| **Load Balancer** | Traefik | Traefik | No migration needed | N/A |
| **Storage** | Backblaze B2 | MinIO | Self-hosting cost effective | Month 12-18 |

---

## Detailed Decision Trees

### 1. Orchestration: K3s vs Nomad

```
START: Are 95%+ of your workloads containers?
├─ YES → Use K3s
│  └─ Are you using Kubernetes ecosystem tools (Kubeflow, KServe)?
│     ├─ YES → Stay K3s permanently
│     └─ NO → Consider Nomad if heterogeneous needs emerge
│
└─ NO → Need to run non-container workloads?
   ├─ Windows VMs needed → Nomad
   ├─ Bare-metal GPU passthrough → Nomad
   ├─ Legacy binaries → Nomad
   └─ All above → Nomad
```

**Metrics to Monitor:**
- Percentage of container vs non-container workloads
- GPU utilization on bare metal vs containerized
- Windows workload requests

**Cost Impact:**
- K3s: $200-2,500/month (same as Nomad)
- Nomad: $200-2,500/month (same hardware)
- Decision is capability, not cost

**Decision:** Start K3s unless you KNOW you need heterogeneous workloads from day 1.

---

### 2. Database (Job Data): PostgreSQL vs TiDB

```
START: Check current write throughput
├─ <10K writes/sec → PostgreSQL single instance
│  └─ Monitor: Add read replicas if read-heavy
│
├─ 10K-50K writes/sec → PostgreSQL with read replicas
│  └─ Monitor: Consider manual sharding at 50K
│
├─ 50K-100K writes/sec → PostgreSQL manual sharding (3-5 instances)
│  └─ Evaluate: Is sharding pain >40hrs/month?
│     ├─ YES → Migrate to TiDB
│     └─ NO → Stay PostgreSQL
│
└─ >100K writes/sec → TiDB auto-sharding
   └─ No question, migrate to TiDB
```

**Specific Triggers (ANY of these):**
1. Write throughput sustained >50K/sec
2. Manual sharding >5 instances
3. Query latency P99 >200ms (despite optimization)
4. Sharding operational overhead >40 hours/month
5. Need distributed transactions across shards

**Metrics to Monitor:**
```sql
-- Write throughput
SELECT count(*) / 60 as writes_per_sec
FROM pg_stat_statements
WHERE query LIKE 'INSERT%' OR query LIKE 'UPDATE%'
AND calls > 0;

-- Query latency P99
SELECT percentile_cont(0.99) WITHIN GROUP (ORDER BY total_time) as p99_latency
FROM pg_stat_statements;

-- Database size (sharding trigger)
SELECT pg_size_pretty(pg_database_size('marketplace'));
```

**Cost Impact:**
- PostgreSQL (single): $80/month
- PostgreSQL (3 shards): $240/month
- PostgreSQL (5 shards): $400/month
- TiDB (15 nodes): $4,500/month
- **Migration justified when operational pain > $4,000/month cost increase**

**Decision:** Don't migrate until you have REAL performance pain.

---

### 3. Database (Financial): CockroachDB

```
START: Do you handle financial transactions?
├─ YES → Use CockroachDB from DAY 1
│  └─ Strong consistency is non-negotiable for money
│
└─ NO → Not applicable (use PostgreSQL/TiDB for job data)
```

**Why CockroachDB for Financial:**
- Strong consistency (no lost money)
- Multi-region replication
- Automatic failover
- Serializable isolation
- Audit trail

**Metrics to Monitor:**
- Transaction volume
- Multi-region latency
- Consistency violations (should be ZERO)

**Cost Impact:**
- 3-node cluster: $2,000/month
- **This is non-negotiable cost for financial integrity**

**Decision:** Always use CockroachDB for user accounts, balances, payments. Never compromise on financial data.

---

### 4. Caching: Valkey vs Redis Enterprise

```
START: How many regions do you operate in?
├─ Single region → Valkey (Redis fork)
│  └─ Set up Sentinel HA (1 primary + 2 replicas)
│
└─ Multi-region → Need multi-region writes?
   ├─ NO (read-only replicas OK) → Valkey with replicas
   ├─ YES → Need active-active? → Redis Enterprise CRDT
   └─ YES → Need <50ms local writes? → Redis Enterprise CRDT
```

**Specific Triggers:**
1. Multi-region deployment with >30% users in secondary region
2. Need active-active writes across regions
3. Global session state required
4. Need <50ms local write latency globally

**Metrics to Monitor:**
```bash
# Cache hit rate
redis-cli INFO stats | grep keyspace_hits

# Latency by region
redis-cli --latency-dist

# Cross-region sync delay (if multi-region)
redis-cli INFO replication | grep master_repl_offset
```

**Cost Impact:**
- Valkey (single region): $60/month
- Valkey (multi-region, read replicas): $180/month
- Redis Enterprise (active-active): $1,000+/month
- **16x cost increase for multi-region writes**

**Decision:** Valkey for single region or read-heavy multi-region. Redis Enterprise only when active-active writes are critical.

---

### 5. Messaging: NATS vs NATS + Kafka

```
START: What is your primary messaging use case?
├─ Job routing / coordination → NATS only
│  └─ Check latency: Is P95 <50ms?
│     ├─ YES → Stay NATS only
│     └─ NO → Investigate backlog (might need Kafka)
│
└─ Event logging / audit trail → Need durable replay?
   ├─ NO → NATS JetStream sufficient
   ├─ YES → Need full event history? → Add Kafka
   └─ YES → Compliance requires audit log? → Add Kafka
```

**Specific Triggers (ANY of these):**
1. Job routing latency P95 >50ms (backlog indicator)
2. Audit/compliance requires durable event replay
3. Analytics needs full event history (last 30+ days)
4. Event volume >1M events/sec sustained
5. Need log compaction for state rebuilding

**Metrics to Monitor:**
```bash
# NATS latency
nats-server --signal=l | grep "Slow Consumers"

# Event volume
nats-server --signal=s | grep "Total Messages"

# JetStream storage
nats-server --signal=s | grep "JetStream Storage"
```

**Cost Impact:**
- NATS only: $30/month
- NATS + Kafka: $1,650/month
- **55x cost increase for dual messaging**

**Decision:** Stay NATS-only unless audit replay or >1M events/sec. JetStream provides sufficient durability for most use cases.

---

### 6. Observability: Prometheus vs VictoriaMetrics

```
START: Check metrics cardinality
├─ <1M active time series → Prometheus sufficient
│  └─ Monitor: Set alert at 8M (approaching limit)
│
├─ 1M-8M active time series → Prometheus OK, monitor closely
│  └─ Prepare: Have VictoriaMetrics migration plan ready
│
├─ 8M-10M active time series → DANGER ZONE
│  └─ MIGRATE: Start VictoriaMetrics migration NOW
│
└─ >10M active time series → Emergency migration required
   └─ VictoriaMetrics required (Prometheus will fail)
```

**Specific Triggers (ANY of these):**
1. Active time series >8M (approaching 10M limit)
2. Query latency P95 >5 seconds
3. Scrape failures due to backlog
4. Storage growth >50GB/day
5. Memory usage >16GB for Prometheus

**Metrics to Monitor:**
```promql
# Active time series
prometheus_tsdb_symbol_table_size_bytes

# Query latency
histogram_quantile(0.95, prometheus_query_duration_seconds_bucket)

# Scrape failures
up == 0

# Storage size
prometheus_tsdb_storage_bytes_total
```

**Cost Impact:**
- Prometheus: $150/month
- VictoriaMetrics: $1,800/month
- **12x cost increase, but necessary for scale**

**Decision:** Prometheus until cardinality >8M. VictoriaMetrics only when Prometheus performance degrades.

---

### 7. Security Layers: Docker → gVisor → Firecracker → SEV-SNP

```
START: What's your security risk profile?
├─ Trusted users (early adopters, beta) → Docker + resource limits
│  └─ Cost: $0/month, Risk: Medium
│
├─ Mix of trusted/untrusted users → Add gVisor for untrusted
│  └─ Cost: $0/month (OSS), Risk: Low-Medium
│
├─ Enterprise customers with compliance → Add Firecracker
│  └─ Cost: $0 software (hardware as needed), Risk: Low
│
└─ Confidential computing (PII/PHI) → Add SEV-SNP
   └─ Cost: $2,000+/month (specialized hardware), Risk: Very Low
```

**Phased Rollout:**
```
Month 1-6: Docker + resource limits
- seccomp profiles
- AppArmor/SELinux
- Resource quotas
- Network policies

Month 6-12: Add gVisor (Tier 2)
- For untrusted workloads
- syscall filtering
- User namespaces
- Cost: $0 (OSS)

Month 12-24: Add Firecracker (Tier 1)
- For high-value workloads
- microVM isolation
- Fast boot (<100ms)
- Cost: $0 software

Month 25+: Add SEV-SNP (Enterprise)
- For confidential computing
- Hardware-based encryption
- Attestation
- Cost: $2,000+/month (hardware)
```

**Decision Triggers:**
- gVisor: When untrusted workloads appear (Month 6-9)
- Firecracker: When enterprise customers demand it (Month 18-24)
- SEV-SNP: When HIPAA/SOC 2 Type II required (Month 25+)

**GPU Workloads:**
- Docker: GPU passthrough works
- gVisor: NO GPU support
- Firecracker: NO GPU support
- Kata Containers: GPU passthrough only
- **Decision: Dedicated GPU nodes per tenant OR NVIDIA MIG (A100/H100)**

---

## Payment Layer Decisions (No Choice - All Required)

### The 4-Layer Payment System

**Layer 1: Compute Capital (Internal)**
```
When to use: ALWAYS (default for all transactions)
Cost: $0.0001 per transaction
Volume: Target 75% of all transactions
Decision: Implement from DAY 1
```

**Layer 2: USDC on Base L2**
```
When to use: Crypto-savvy users, >$50 transactions
Cost: $0.01 per transaction
Volume: Target 13% of transactions
Decision: Implement from DAY 1
```

**Layer 3: Lightning Network**
```
When to use: Micropayments <$10, Bitcoin users
Cost: $0.001 per transaction
Volume: Target 2% of transactions
Decision: Implement at Month 3-6
```

**Layer 4: Stripe Connect**
```
When to use: Fiat withdrawals ONLY (minimize usage)
Cost: 3% + $0.30 per transaction
Volume: Target 10% of transactions (withdrawals)
Decision: Implement from DAY 1 (on-ramps)
```

**Critical Success Factor:** Keep 75%+ transactions in Layer 1 (Compute Capital). Every transaction that stays in-system saves 3% in fees.

---

## P2P Architecture Decisions (Non-Negotiable)

### WebRTC Implementation

```
Decision Tree: Is there a decision?
└─ NO → WebRTC P2P is REQUIRED
   └─ Economics are impossible without it
      └─ 98% bandwidth cost savings
         └─ Platform coordinates, NEVER proxies data
```

**Non-Negotiable Requirements:**
1. WebRTC for all data transfer
2. STUN/TURN infrastructure (self-hosted)
3. Target: >95% direct connections
4. TURN relay: <5% of connections
5. Platform: Coordinator only, never proxy

**Metrics to Monitor:**
```javascript
// Connection success rate
const directRate = directConnections / totalConnections;
// Target: >95%

// TURN usage
const turnRate = turnConnections / totalConnections;
// Target: <5%

// Connection time
const p95ConnectionTime = percentile(connectionTimes, 0.95);
// Target: <1500ms
```

**Cost Impact:**
- Without P2P (CloudFront): $39,050/month for 1PB
- With P2P (95% direct): $880/month
- **$38,170/month savings (98% reduction)**

**Decision:** No decision needed. P2P is required for economic survival.

---

## Migration Risk Assessment

### Low-Risk Migrations (Do When Needed)
```
✅ PostgreSQL → read replicas
✅ Docker → gVisor (can rollback)
✅ Single region → multi-region TURN
✅ Backblaze B2 → MinIO
```

### Medium-Risk Migrations (Plan Carefully)
```
⚠️ PostgreSQL → manual sharding (complex but reversible)
⚠️ Prometheus → VictoriaMetrics (PromQL compatible)
⚠️ NATS → NATS + Kafka (additive, can remove Kafka)
⚠️ Valkey → Redis Enterprise (migration path exists)
```

### High-Risk Migrations (Test Extensively)
```
❌ PostgreSQL → TiDB (different architecture)
❌ K3s → Nomad (major workflow change)
❌ gVisor → Firecracker (workload migration)
```

**General Rule:** Prefer additive changes over replacements. Can always add capacity, harder to replace core infrastructure.

---

## Cost Optimization Checklist

Before migrating to a more expensive component, verify:

```
☐ Current metrics breach thresholds (70%+ of limit)
☐ Alternative optimizations exhausted (indexes, caching, etc.)
☐ Performance SLA actually affected (not just approaching limit)
☐ Operational pain quantified (hours/week managing current system)
☐ Migration plan documented (rollback strategy exists)
☐ Team trained on new technology (or training scheduled)
☐ Budget approved (cost increase justified by revenue)
☐ Timeline realistic (not emergency migration)
```

If ANY checkbox is unchecked, reconsider the migration.

---

## Financial Justification Framework

### When to Migrate (ROI Calculation)

```
Migration Cost = (Setup Time × Engineer Hourly Rate) + (Monthly Cost Increase × 12)

Operational Savings = (Current Ops Hours × Hourly Rate × 12)
Performance Value = (Customer Churn Prevented × LTV)

Total Benefit = Operational Savings + Performance Value

ROI = (Total Benefit - Migration Cost) / Migration Cost

Decision:
- ROI >100%: Migrate now
- ROI 50-100%: Migrate in next quarter
- ROI 0-50%: Defer 6-12 months
- ROI <0%: Don't migrate
```

**Example: PostgreSQL → TiDB**
```
Migration Cost:
- Setup: 160 hours × $100/hr = $16,000
- Annual cost increase: ($4,500 - $240) × 12 = $51,120
- TOTAL: $67,120

Operational Savings:
- Sharding management: 40 hrs/month × $100/hr × 12 = $48,000
- Reduced incidents: 20 hrs/month × $100/hr × 12 = $24,000
- TOTAL: $72,000

Performance Value:
- Prevent churn: 100 users × $500 LTV = $50,000

Total Benefit: $72,000 + $50,000 = $122,000

ROI = ($122,000 - $67,120) / $67,120 = 82%

Decision: Migrate in next quarter (ROI 50-100%)
```

---

## Quick Reference: "Should I Migrate?" Flowchart

```
START: Considering migration to Vision B component?
│
├─ Are current metrics >70% of limits?
│  ├─ NO → DON'T MIGRATE (premature)
│  └─ YES → Continue
│
├─ Have you exhausted optimizations?
│  ├─ NO → OPTIMIZE FIRST (indexes, caching, etc.)
│  └─ YES → Continue
│
├─ Is performance actually impacting users?
│  ├─ NO → DON'T MIGRATE (not urgent)
│  └─ YES → Continue
│
├─ Is operational pain >20 hrs/week?
│  ├─ NO → DEFER 3-6 MONTHS (manageable)
│  └─ YES → Continue
│
├─ Is ROI >50%?
│  ├─ NO → DON'T MIGRATE (not justified)
│  └─ YES → Continue
│
├─ Do you have budget approval?
│  ├─ NO → GET APPROVAL FIRST
│  └─ YES → Continue
│
├─ Do you have rollback plan?
│  ├─ NO → DOCUMENT ROLLBACK
│  └─ YES → Continue
│
└─ MIGRATE NOW
   └─ Monitor metrics closely post-migration
```

---

## Emergency Migration Scenarios

### When to Bypass Framework (Immediate Migration)

**Scenario 1: Hard Limit Hit**
```
Prometheus cardinality >10M
PostgreSQL write throughput >100K/sec
Database storage >95% full
Memory OOM kills happening

Action: Emergency migration, no waiting
```

**Scenario 2: Security Breach**
```
Container escape detected
Untrusted code accessing host
Data exfiltration attempt

Action: Deploy Firecracker/gVisor immediately
```

**Scenario 3: Compliance Mandate**
```
SOC 2 audit requires confidential computing
HIPAA compliance deadline
Financial audit requires stronger consistency

Action: Deploy required component (SEV-SNP, CockroachDB, etc.)
```

**Emergency Process:**
1. Acknowledge emergency (skip normal approval)
2. Deploy minimum viable migration
3. Document decision retroactively
4. Review in next post-mortem

---

## Summary: The Golden Rules

1. **Start Simple:** Vision A until metrics prove otherwise
2. **Measure Everything:** Data-driven decisions only
3. **70% Threshold:** Start planning migration at 70% of limits
4. **Avoid Premature Optimization:** Most expensive waste
5. **Payment First:** Optimize payments before infrastructure
6. **P2P Non-Negotiable:** Required for economic survival
7. **Financial Data: CockroachDB:** Always, from day 1
8. **When Unsure: Don't Migrate:** Vision A sufficient until proven otherwise

---

**Document Status:** ✅ Complete
**Purpose:** Quick decision reference for migrations
**Usage:** Check this before any architecture migration
**Update Frequency:** Quarterly based on metrics analysis

**Version:** 1.0
**Date:** October 14, 2025
**Author:** Architecture Synthesis Agent 1
