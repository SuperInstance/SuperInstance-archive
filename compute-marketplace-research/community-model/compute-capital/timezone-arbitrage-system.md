# Timezone Arbitrage System Design

**Document Version:** 1.0
**Date:** October 14, 2025
**Status:** Research Complete - Ready for Implementation

---

## Executive Summary

**Timezone arbitrage** is the killer feature that makes Compute Capital a game-changer. Instead of individuals owning expensive hardware that sits idle 16+ hours per day, **compute circles** of 3-8 people across different timezones share machines to achieve **24/7 utilization** at **1/3 the cost**.

**The Vision:**
```
3 developers (US, Europe, Asia) each buy a $5K workstation
- Developer A (San Francisco): Works 9am-5pm PST, uses own machine
- Developer B (London): Works 9am-5pm GMT, uses Developer A's machine (idle 1am-9am PST)
- Developer C (Singapore): Works 9am-5pm SGT, uses Developer B's machine (idle 1am-9am GMT)

Result:
- Each developer pays $5K but gets access to 3x machines
- Effective cost: $1,667 per person for triple the compute power
- Total utilization: 72 hours used / 72 hours available = 100%
- Everyone works 8 hours/day on high-end hardware
```

This document defines the **scheduling algorithms**, **matching systems**, **time slot reservations**, and **group contract mechanics** needed to make timezone arbitrage work seamlessly.

---

## Table of Contents

1. [Core Concept and Economics](#core-concept-and-economics)
2. [Compute Circle Models](#compute-circle-models)
3. [Matching Algorithm Design](#matching-algorithm-design)
4. [Time Slot Reservation System](#time-slot-reservation-system)
5. [Group Contract Mechanics](#group-contract-mechanics)
6. [Failover and Reliability](#failover-and-reliability)
7. [Pricing and Cost Savings](#pricing-and-cost-savings)
8. [Implementation Roadmap](#implementation-roadmap)

---

## Core Concept and Economics

### The Problem: Idle Hardware

**Current State (No Sharing):**
```
Developer buys $5,000 RTX 4090 workstation
Uses it 8 hours/day for work (9am-5pm)
Idle 16 hours/day + weekends

Utilization: 8 hours / 24 hours = 33.3%
Cost per active hour: $5,000 / (8 × 365) = $1.71/hour
Wasted capacity: 16 hours/day × $1.71 = $27.40/day wasted
```

**Problem Summary:**
- **$27.40/day** in idle hardware ($10K+/year in wasted capacity)
- High upfront capital cost ($5K)
- Single point of failure (if machine breaks, developer stuck)
- No access to variety (can't test on different GPUs)

### The Solution: Timezone Arbitrage

**New State (3-Person Compute Circle):**
```
Three developers, three timezones, three machines

Machine Distribution:
┌─────────────────────────────────────────────────────────────────┐
│ Time (UTC)  00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23 │
├─────────────────────────────────────────────────────────────────┤
│ Developer A (US - PST, UTC-8)                                   │
│   Uses own machine:    [-----SLEEP-----][---WORK A---][--SLEEP--] │
│   Uses B's machine:    [---WORK A---][----SLEEP-----]             │
│                                                                   │
│ Developer B (UK - GMT, UTC+0)                                   │
│   Uses own machine:    [--SLEEP--][---WORK B---][----SLEEP-----] │
│   Uses C's machine:    [---WORK B---][----SLEEP-----]             │
│                                                                   │
│ Developer C (Singapore - SGT, UTC+8)                            │
│   Uses own machine:    [----SLEEP-----][---WORK C---][--SLEEP--] │
│   Uses A's machine:    [---WORK C---][----SLEEP-----]             │
└─────────────────────────────────────────────────────────────────┘

Result: 100% utilization, 33% cost per person
```

**Economic Model:**
```
Total hardware investment: 3 × $5,000 = $15,000
Divided by 3 people = $5,000 each (same as before)

But now each person gets:
- Their own machine (8 hours/day)
- Access to 2 other machines (16 hours/day if needed)
- Redundancy (if one machine fails, use another)
- Variety (test on different GPU configs)

Effective cost per person: $5,000 / 3 machines = $1,667 per machine
Cost savings: 66% reduction in per-machine cost
```

### Key Insight: Non-Overlapping Work Hours

**The Magic Formula:**
```
24 hours ÷ 8-hour workday = 3 optimal timezone slots

Slot 1 (Americas): UTC-8 to UTC-5 → 9am-5pm PST/MST/CST/EST
Slot 2 (Europe/Africa): UTC+0 to UTC+3 → 9am-5pm GMT/CET/EET
Slot 3 (Asia/Pacific): UTC+8 to UTC+11 → 9am-5pm SGT/JST/AEST

Zero overlap = 100% utilization
```

**Why This Works:**
- When US developer sleeps (8pm-8am PST), machine available for Europe/Asia
- When Europe developer sleeps (8pm-8am GMT), machine available for Asia/US
- When Asia developer sleeps (8pm-8am SGT), machine available for US/Europe
- Round-robin = perfect distribution

---

## Compute Circle Models

### Model 1: 3-Person Circle (Optimal for Individuals)

**Configuration:**
```
Members: 3 developers
Machines: 3 (one per member)
Timezones: Americas, Europe, Asia (8-hour offsets)
Commitment: 6-12 months
```

**Time Distribution:**
```
Each member:
- Primary slot (8 hours): Own machine, guaranteed access
- Secondary slot (8 hours): Partner's machine, first-priority backup
- Tertiary slot (8 hours): Partner's machine, second-priority backup

Total: 24-hour coverage with 3 machines
```

**Benefits:**
- Simple coordination (only 3 people)
- Clear ownership (one machine per person)
- Minimal scheduling conflicts
- Easy to settle disputes (2-of-3 vote)

**Use Case:** Freelancers, indie developers, researchers

### Model 2: 4-Person Circle (Extended Coverage)

**Configuration:**
```
Members: 4 developers
Machines: 4 (one per member)
Timezones: West US, East US/South America, Europe, Asia
Commitment: 6-12 months
```

**Time Distribution:**
```
Slot 1 (6 hours): US West Coast (9am-3pm PST)
Slot 2 (6 hours): US East Coast (12pm-6pm PST / 3pm-9pm EST)
Slot 3 (6 hours): Europe (9pm-3am PST / 9am-3pm CET)
Slot 4 (6 hours): Asia (3am-9am PST / 9am-3pm SGT)

Total: 24-hour coverage with 4 machines
```

**Benefits:**
- Finer-grained time slots
- More backup options (3 redundant machines)
- Can accommodate varied schedules
- Better for part-time usage

**Use Case:** Part-time developers, teams with flexible hours

### Model 3: 8-Person Enterprise Circle

**Configuration:**
```
Members: 8 companies/teams
Machines: 8 high-end servers (H100, A100)
Timezones: Global distribution
Commitment: 12-36 months
```

**Time Distribution:**
```
Each member gets:
- 3-hour guaranteed primary slot
- Access to 7 other machines during off-hours
- Redundancy across multiple timezones

Example: AI Research Lab
- Primary slot: 9am-12pm (critical ML training)
- Extended usage: 12pm-5pm (lower priority, shared)
- Off-hours: Available for batch jobs on other machines
```

**Benefits:**
- Enterprise-grade redundancy
- Cost sharing for expensive hardware ($30K+ H100s)
- Access to diverse GPU types (mix of H100, A100, A6000)
- Professional SLAs and contracts

**Use Case:** Startups, research labs, small enterprises

### Model 4: Asymmetric Circles (Mixed Hardware)

**Configuration:**
```
Not all machines are equal

Member A: RTX 4090 workstation ($5K)
Member B: RTX 4060 laptop ($2K)
Member C: H100 server ($30K)

Problem: Unfair value exchange
```

**Solution: Performance-Weighted Allocation**
```
Calculate "CC value" of each machine:
- RTX 4060: 0.5 CC/hour → 4 CC/day (8 hours)
- RTX 4090: 1.0 CC/hour → 8 CC/day (8 hours)
- H100: 4.5 CC/hour → 36 CC/day (8 hours)

Total pool: 4 + 8 + 36 = 48 CC/day

Member A contributes 8 CC (16.7% of pool) → Gets 16.7% of total time
Member B contributes 4 CC (8.3% of pool) → Gets 8.3% of total time
Member C contributes 36 CC (75% of pool) → Gets 75% of total time

Members can "spend" their allocation on any machine in the circle
```

**Example:**
```
Member A (RTX 4090 owner) has 8 CC/day to spend:
- Spends 4 CC using own machine (4 hours)
- Spends 4 CC using H100 (0.89 hours = 53 minutes)
- Result: 4 hours on RTX 4090 + 53 minutes on H100

Member C (H100 owner) has 36 CC/day to spend:
- Spends 18 CC using own H100 (4 hours)
- Spends 10 CC using RTX 4090 (10 hours for testing game)
- Spends 8 CC using RTX 4060 (16 hours for light tasks)
- Result: Full flexibility across all hardware tiers
```

**Benefits:**
- Fair value exchange regardless of hardware
- Enables participation from budget and premium users
- Allows "upgrading" by pooling resources
- Creates natural marketplace dynamics

---

## Matching Algorithm Design

### Goal: Automatically Find Compatible Circle Members

**Inputs:**
```javascript
{
  user_id: "user_12345",
  timezone: "America/Los_Angeles",  // IANA timezone
  work_hours: {
    start: "09:00",  // Local time
    end: "17:00"
  },
  work_days: ["monday", "tuesday", "wednesday", "thursday", "friday"],
  hardware: {
    cpu: "AMD Ryzen 9 7950X",
    gpu: "NVIDIA RTX 4090",
    ram_gb: 64,
    benchmark_score: 1.0  // Normalized to reference
  },
  preferences: {
    circle_size: 3,  // Preferred number of members
    min_hardware_tier: 0.8,  // Only match with similar/better hardware
    commitment_months: 12,
    languages: ["English"],
    max_latency_ms: 50  // Network latency requirement
  }
}
```

**Outputs:**
```javascript
{
  matches: [
    {
      circle_id: "circle_789",
      members: [
        {user_id: "user_12345", timezone: "America/Los_Angeles", ...},
        {user_id: "user_67890", timezone: "Europe/London", ...},
        {user_id: "user_54321", timezone: "Asia/Singapore", ...}
      ],
      compatibility_score: 0.95,  // 0-1 scale
      time_coverage: "100%",  // Percentage of 24 hours covered
      hardware_balance: 0.98,  // How evenly matched hardware is
      estimated_savings: "$3,334/year"
    }
  ]
}
```

### Matching Algorithm (Pseudocode)

```python
def find_optimal_circles(user_profile, existing_circles, all_users):
    """
    Find the best compute circle matches for a user.

    Strategy:
    1. Filter users by timezone compatibility (non-overlapping work hours)
    2. Filter by hardware compatibility (similar performance tiers)
    3. Score potential circles by multiple factors
    4. Return top N matches
    """

    # Step 1: Timezone Filtering
    timezone_compatible_users = []
    user_work_utc = convert_to_utc(user_profile.work_hours, user_profile.timezone)

    for candidate in all_users:
        candidate_work_utc = convert_to_utc(
            candidate.work_hours,
            candidate.timezone
        )

        # Calculate overlap between work hours
        overlap_hours = calculate_time_overlap(user_work_utc, candidate_work_utc)

        # Accept if overlap < 2 hours (some flexibility for meetings)
        if overlap_hours < 2:
            timezone_compatible_users.append({
                "user": candidate,
                "overlap_hours": overlap_hours,
                "timezone_offset": calculate_offset(
                    user_profile.timezone,
                    candidate.timezone
                )
            })

    # Step 2: Hardware Filtering
    hardware_compatible_users = []
    user_benchmark = user_profile.hardware.benchmark_score

    for candidate in timezone_compatible_users:
        candidate_benchmark = candidate.user.hardware.benchmark_score

        # Check if within acceptable range
        if candidate_benchmark >= user_profile.preferences.min_hardware_tier:
            hardware_ratio = candidate_benchmark / user_benchmark
            hardware_compatible_users.append({
                **candidate,
                "hardware_ratio": hardware_ratio
            })

    # Step 3: Circle Formation
    potential_circles = []
    target_size = user_profile.preferences.circle_size

    if target_size == 3:
        # Find two partners that together create perfect coverage
        for partner1 in hardware_compatible_users:
            for partner2 in hardware_compatible_users:
                if partner1 == partner2:
                    continue

                circle = [user_profile, partner1.user, partner2.user]

                # Check if this circle covers 24 hours with minimal overlap
                coverage_score = calculate_time_coverage(circle)

                if coverage_score > 0.85:  # At least 85% coverage
                    potential_circles.append({
                        "members": circle,
                        "coverage_score": coverage_score
                    })

    elif target_size == 4:
        # Similar logic for 4-person circles
        # (Algorithm expands but same concept)
        pass

    # Step 4: Score and Rank Circles
    scored_circles = []
    for circle in potential_circles:
        score = calculate_circle_score(circle, user_profile)
        scored_circles.append({
            **circle,
            "compatibility_score": score
        })

    # Sort by score (highest first)
    scored_circles.sort(key=lambda x: x["compatibility_score"], reverse=True)

    return scored_circles[:10]  # Return top 10 matches


def calculate_circle_score(circle, user_profile):
    """
    Multi-factor scoring function.

    Factors:
    - Time coverage (40% weight)
    - Hardware balance (25% weight)
    - Geographic diversity (15% weight)
    - Language compatibility (10% weight)
    - Network latency (10% weight)
    """

    # Factor 1: Time Coverage (higher is better)
    coverage = calculate_time_coverage(circle["members"])
    coverage_score = min(coverage / 0.95, 1.0)  # Target 95%+

    # Factor 2: Hardware Balance (closer to 1.0 is better)
    benchmarks = [m.hardware.benchmark_score for m in circle["members"]]
    avg_benchmark = sum(benchmarks) / len(benchmarks)
    variance = sum((b - avg_benchmark)**2 for b in benchmarks) / len(benchmarks)
    hardware_score = 1.0 / (1.0 + variance)  # Lower variance = higher score

    # Factor 3: Geographic Diversity (more spread = better redundancy)
    timezones = [m.timezone for m in circle["members"]]
    unique_regions = len(set(get_region(tz) for tz in timezones))
    geo_score = unique_regions / len(circle["members"])

    # Factor 4: Language Compatibility
    user_languages = set(user_profile.preferences.languages)
    compatible_members = sum(
        1 for m in circle["members"]
        if any(lang in m.languages for lang in user_languages)
    )
    language_score = compatible_members / len(circle["members"])

    # Factor 5: Network Latency
    latencies = [
        estimate_latency(user_profile.location, m.location)
        for m in circle["members"]
    ]
    avg_latency = sum(latencies) / len(latencies)
    latency_score = 1.0 - (avg_latency / user_profile.preferences.max_latency_ms)
    latency_score = max(0, min(1, latency_score))

    # Weighted average
    final_score = (
        0.40 * coverage_score +
        0.25 * hardware_score +
        0.15 * geo_score +
        0.10 * language_score +
        0.10 * latency_score
    )

    return final_score


def calculate_time_coverage(members):
    """
    Calculate what percentage of 24 hours is covered by member work hours.

    Goal: Maximize coverage, minimize overlap.
    """

    # Create 24-hour timeline (in UTC)
    timeline = [0] * 24  # Hour 0-23

    for member in members:
        work_hours_utc = convert_to_utc(member.work_hours, member.timezone)
        start_hour = int(work_hours_utc.start)
        end_hour = int(work_hours_utc.end)

        # Mark covered hours
        for hour in range(start_hour, end_hour):
            timeline[hour % 24] += 1

    # Calculate coverage
    covered_hours = sum(1 for count in timeline if count > 0)
    total_coverage = covered_hours / 24

    # Penalize overlap (when multiple people want same time slot)
    overlap_penalty = sum(max(0, count - 1) for count in timeline) / 24

    adjusted_coverage = total_coverage - (0.5 * overlap_penalty)

    return max(0, adjusted_coverage)


def estimate_latency(location1, location2):
    """
    Estimate network latency between two locations.

    Uses geographic distance as proxy.
    Formula: latency_ms ≈ (distance_km / 200) + base_latency

    Base latency:
    - Same city: 5ms
    - Same country: 20ms
    - Same continent: 50ms
    - Cross-ocean: 150ms+
    """

    distance_km = haversine_distance(location1, location2)

    if distance_km < 100:  # Same city
        return 5 + (distance_km / 200)
    elif distance_km < 1000:  # Same country
        return 20 + (distance_km / 200)
    elif distance_km < 5000:  # Same continent
        return 50 + (distance_km / 200)
    else:  # Cross-ocean
        return 150 + (distance_km / 200)
```

### Matching Interface (User Experience)

**Step 1: User Profile Setup**
```
"Let's find your ideal compute circle!"

1. What are your typical work hours?
   [Dropdown: 9:00 AM] to [Dropdown: 5:00 PM]
   [Timezone: America/Los_Angeles ▼]

2. What hardware do you have?
   [Auto-detected: RTX 4090, Ryzen 9 7950X, 64GB RAM]
   Performance tier: ★★★★★ High-End

3. How many people in your circle?
   ○ 3 people (recommended for individuals)
   ● 4 people (more flexibility)
   ○ 8 people (enterprise teams)

4. What's your commitment level?
   ○ 6 months
   ● 12 months (recommended)
   ○ 24 months

[Find My Circle →]
```

**Step 2: Match Results**
```
Found 7 compatible circles for you!

┌───────────────────────────────────────────────────────┐
│ 🥇 BEST MATCH - Circle #1 (95% compatibility)        │
├───────────────────────────────────────────────────────┤
│ Members:                                              │
│  • You (US - PST) - RTX 4090 - 9am-5pm               │
│  • Alex K. (UK - GMT) - RTX 4090 - 9am-5pm          │
│  • Jun L. (Singapore - SGT) - RTX 4090 - 9am-5pm    │
│                                                       │
│ Coverage: 100% of 24 hours                           │
│ Overlap: 0 hours (perfect!)                          │
│ Hardware Match: ★★★★★ (all equivalent)              │
│ Est. Savings: $3,334/year per person                 │
│                                                       │
│ [View Details] [Join Circle]                         │
└───────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────┐
│ 🥈 GOOD MATCH - Circle #2 (88% compatibility)        │
│ ...                                                   │
└───────────────────────────────────────────────────────┘
```

**Step 3: Circle Agreement**
```
You're about to join Circle #789 with Alex K. and Jun L.

Review the terms:
✓ 12-month commitment (Nov 2025 - Nov 2026)
✓ Guaranteed access: 9am-5pm PST (your primary slot)
✓ Backup access: Alex's machine (1am-9am PST) or Jun's machine (5pm-1am PST)
✓ Performance tier: High-End (RTX 4090 equivalent)
✓ SLA: 99% uptime or proportional refund

Cost:
- Your contribution: 8 CC/day ($0.80/day) ← You earn this by providing your machine
- Your access: 24 CC/day of compute capacity (3x machines)
- Net savings: 66% vs solo ownership

[Sign Agreement] [← Back]
```

---

## Time Slot Reservation System

### Reservation Types

#### 1. Primary Slots (Guaranteed)

**Definition:** Your dedicated time slot on your own machine.

**Characteristics:**
```
- Always available (100% guarantee)
- Highest priority (cannot be bumped)
- No additional cost (you own the machine)
- Can be scheduled recurring (Mon-Fri, 9am-5pm)
```

**Example:**
```
Developer A owns Machine 1
Primary slot: Mon-Fri, 9am-5pm PST

This time is sacred - no one else can use Machine 1 during this window.
```

#### 2. Secondary Slots (Scheduled)

**Definition:** Reserved time on circle partners' machines.

**Characteristics:**
```
- Must be scheduled in advance (24-hour notice)
- High priority (only primary slot owner can bump)
- Small premium (1.1x CC rate vs spot pricing)
- Limited to circle members only
```

**Example:**
```
Developer A wants to run overnight job on Developer B's machine
Schedules: Tonight, 8pm PST - 6am PST (10 hours)
Cost: 10 hours × 1.0 CC/hour × 1.1 premium = 11 CC
Status: Confirmed (B's primary slot is 1am-9am GMT, no conflict)
```

#### 3. Spot Slots (First-Come-First-Served)

**Definition:** Unscheduled time available immediately.

**Characteristics:**
```
- No advance reservation
- Lowest priority (can be bumped if owner needs machine)
- Discounted rate (0.8x CC vs scheduled)
- Available to entire marketplace (not just circle)
```

**Example:**
```
Developer A's machine idle at 2am PST (A is sleeping)
Developer C (or anyone) can start a spot job:
  - Rate: 1.0 CC/hour × 0.8 discount = 0.8 CC/hour
  - Risk: If A wakes up and needs machine, job paused and migrated
  - Best for: Interruptible batch jobs, ML training with checkpoints
```

### Reservation Database Schema

```sql
-- Time slot reservations
CREATE TABLE compute_reservations (
    id UUID PRIMARY KEY,
    circle_id UUID REFERENCES compute_circles(id),
    machine_id UUID REFERENCES machines(id),
    user_id UUID REFERENCES users(id),

    -- Reservation type
    slot_type VARCHAR(20) CHECK (slot_type IN ('primary', 'secondary', 'spot')),

    -- Time window
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_hours DECIMAL(10,2),  -- Calculated: end_time - start_time

    -- Recurrence (for weekly schedules)
    is_recurring BOOLEAN DEFAULT FALSE,
    recurrence_pattern VARCHAR(100),  -- e.g., "every Monday-Friday"
    recurrence_end_date DATE,

    -- Pricing
    cc_rate_per_hour DECIMAL(10,4),  -- CC cost per hour
    total_cc_cost DECIMAL(10,2),  -- total_hours × cc_rate

    -- Status
    status VARCHAR(20) CHECK (status IN ('pending', 'confirmed', 'active', 'completed', 'cancelled', 'bumped')),

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CHECK (end_time > start_time),
    CHECK (duration_hours > 0)
);

-- Index for efficient queries
CREATE INDEX idx_reservations_machine_time
ON compute_reservations(machine_id, start_time, end_time);

CREATE INDEX idx_reservations_user_time
ON compute_reservations(user_id, start_time, end_time);
```

### Conflict Detection Algorithm

```python
def check_reservation_conflicts(machine_id, start_time, end_time):
    """
    Check if a new reservation conflicts with existing ones.

    Conflict rules:
    1. Primary slots block everything
    2. Secondary slots block other secondary + spot
    3. Spot slots can coexist (multiple spot jobs on multi-GPU machines)

    Returns:
        {
            "has_conflict": bool,
            "conflicting_reservations": [reservation_ids],
            "suggestion": alternative_time_slot
        }
    """

    # Query existing reservations for this machine
    overlapping_reservations = db.query("""
        SELECT * FROM compute_reservations
        WHERE machine_id = %s
          AND status IN ('confirmed', 'active')
          AND (
              (start_time <= %s AND end_time > %s) OR
              (start_time < %s AND end_time >= %s) OR
              (start_time >= %s AND end_time <= %s)
          )
        ORDER BY slot_type, start_time
    """, (machine_id, start_time, start_time, end_time, end_time, start_time, end_time))

    # Check for conflicts
    for reservation in overlapping_reservations:
        if reservation.slot_type == 'primary':
            # Primary slots block everything
            return {
                "has_conflict": True,
                "conflicting_reservations": [reservation.id],
                "reason": f"Owner has primary slot {reservation.start_time} - {reservation.end_time}",
                "suggestion": find_next_available_slot(machine_id, duration_hours)
            }

        elif reservation.slot_type == 'secondary':
            # Secondary slots block other secondary slots
            # (Spot slots can be bumped, so not a hard conflict)
            return {
                "has_conflict": True,
                "conflicting_reservations": [reservation.id],
                "reason": "Another circle member has scheduled this time",
                "suggestion": find_next_available_slot(machine_id, duration_hours)
            }

    # No conflicts found
    return {
        "has_conflict": False,
        "conflicting_reservations": [],
        "suggestion": None
    }


def find_next_available_slot(machine_id, duration_hours, start_search=None):
    """
    Find the next available time slot of given duration.

    Strategy:
    1. Get all existing reservations
    2. Find gaps between reservations
    3. Return first gap >= duration_hours
    """

    if start_search is None:
        start_search = datetime.now()

    # Get all future reservations (next 7 days)
    end_search = start_search + timedelta(days=7)
    reservations = db.query("""
        SELECT start_time, end_time, slot_type
        FROM compute_reservations
        WHERE machine_id = %s
          AND start_time <= %s
          AND end_time >= %s
          AND status IN ('confirmed', 'active')
        ORDER BY start_time
    """, (machine_id, end_search, start_search))

    # Build timeline of busy periods
    busy_periods = []
    for res in reservations:
        if res.slot_type in ['primary', 'secondary']:
            busy_periods.append((res.start_time, res.end_time))

    # Merge overlapping busy periods
    busy_periods = merge_intervals(busy_periods)

    # Find gaps
    current_time = start_search
    for busy_start, busy_end in busy_periods:
        gap_duration = (busy_start - current_time).total_seconds() / 3600

        if gap_duration >= duration_hours:
            return {
                "start_time": current_time,
                "end_time": current_time + timedelta(hours=duration_hours),
                "duration_hours": duration_hours
            }

        current_time = busy_end

    # Check remaining time after last busy period
    gap_duration = (end_search - current_time).total_seconds() / 3600
    if gap_duration >= duration_hours:
        return {
            "start_time": current_time,
            "end_time": current_time + timedelta(hours=duration_hours),
            "duration_hours": duration_hours
        }

    # No availability in next 7 days
    return None
```

---

## Group Contract Mechanics

### Circle Formation Agreement

```markdown
# COMPUTE CIRCLE AGREEMENT

**Circle ID:** circle-789
**Formation Date:** November 1, 2025
**Term:** 12 months (November 1, 2025 - October 31, 2026)

## PARTIES

**Member A (Circle Coordinator):**
- Name: Developer A
- Location: San Francisco, CA, USA
- Timezone: America/Los_Angeles (UTC-8)
- Machine: RTX 4090 + Ryzen 9 7950X (Performance: 1.0 CC/hour)
- Primary Slot: Monday-Friday, 9:00am-5:00pm PST

**Member B:**
- Name: Developer B
- Location: London, UK
- Timezone: Europe/London (UTC+0)
- Machine: RTX 4090 + Ryzen 9 7950X (Performance: 1.0 CC/hour)
- Primary Slot: Monday-Friday, 9:00am-5:00pm GMT

**Member C:**
- Name: Developer C
- Location: Singapore
- Timezone: Asia/Singapore (UTC+8)
- Machine: RTX 4090 + Ryzen 9 7950X (Performance: 1.0 CC/hour)
- Primary Slot: Monday-Friday, 9:00am-5:00pm SGT

## TERMS

### 1. Resource Sharing
- Each member contributes their machine to the circle's shared pool.
- Each member receives access to all machines in the circle.
- Access is governed by the slot priority system (primary > secondary > spot).

### 2. Time Allocation
- Each member has an exclusive "primary slot" on their own machine (8 hours/day, 5 days/week).
- Each member can schedule "secondary slots" on other members' machines with 24-hour notice.
- Each member can use "spot slots" on idle machines without notice (subject to availability).

### 3. Fair Usage
- Each member contributes 1.0 CC/hour of compute capacity (8 CC/day during work hours).
- Each member can consume up to 3.0 CC/hour across all machines (24 CC/day potential).
- Over-usage beyond fair share may incur premium rates or require approval.

### 4. Service Level Agreement (SLA)
- Each member commits to 99% uptime during their committed hours.
- Downtime > 1%: Proportional CC credit to affected members.
- Downtime > 5%: Circle may vote to remove member with 2/3 majority.

### 5. Exit Conditions
- Any member may exit with 30 days' notice.
- Exiting member must help find replacement or pay early termination fee (1 month of CC contribution).
- Circle dissolves if membership drops below 2 members.

### 6. Dispute Resolution
- Technical disputes (e.g., uptime claims) resolved via platform metrics.
- Non-technical disputes (e.g., behavior) resolved via 2/3 majority vote.
- Platform reserves final decision-making authority.

### 7. Cost Sharing
- No direct payments between members.
- All transactions occur via Compute Capital (CC).
- Platform fees (10%) apply to all transactions.

## SIGNATURES

[Digital signatures from all members via platform]
```

### Smart Contract Implementation (Optional)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title ComputeCircle
 * @dev Manages compute circle agreements and enforces terms on-chain
 */
contract ComputeCircle {

    struct Member {
        address walletAddress;
        string machineId;
        uint256 ccPerHourContribution;  // Performance-weighted
        uint256 primarySlotStart;  // Unix timestamp
        uint256 primarySlotEnd;
        bool active;
    }

    struct Circle {
        string circleId;
        uint256 formationDate;
        uint256 expirationDate;
        uint256 minUptime;  // Basis points (9900 = 99%)
        Member[] members;
        uint256 totalCCPool;  // Sum of all member contributions
        mapping(address => uint256) ccBalances;  // Track usage
    }

    mapping(string => Circle) public circles;

    event CircleFormed(string indexed circleId, address[] members);
    event MemberAdded(string indexed circleId, address member);
    event MemberRemoved(string indexed circleId, address member, string reason);
    event UptimeViolation(string indexed circleId, address member, uint256 actualUptime);

    /**
     * @dev Create a new compute circle
     */
    function createCircle(
        string memory circleId,
        uint256 durationMonths,
        uint256 minUptime,
        Member[] memory initialMembers
    ) external {
        require(circles[circleId].formationDate == 0, "Circle already exists");
        require(initialMembers.length >= 2, "Minimum 2 members required");

        Circle storage circle = circles[circleId];
        circle.circleId = circleId;
        circle.formationDate = block.timestamp;
        circle.expirationDate = block.timestamp + (durationMonths * 30 days);
        circle.minUptime = minUptime;

        uint256 totalCC = 0;
        address[] memory memberAddresses = new address[](initialMembers.length);

        for (uint256 i = 0; i < initialMembers.length; i++) {
            circle.members.push(initialMembers[i]);
            totalCC += initialMembers[i].ccPerHourContribution;
            memberAddresses[i] = initialMembers[i].walletAddress;

            // Initialize CC balance
            circle.ccBalances[initialMembers[i].walletAddress] = 0;
        }

        circle.totalCCPool = totalCC;

        emit CircleFormed(circleId, memberAddresses);
    }

    /**
     * @dev Record compute usage (called by platform backend)
     */
    function recordUsage(
        string memory circleId,
        address user,
        uint256 ccAmount
    ) external {
        Circle storage circle = circles[circleId];
        require(circle.formationDate > 0, "Circle does not exist");
        require(block.timestamp < circle.expirationDate, "Circle expired");

        // Deduct from user's balance
        circle.ccBalances[user] += ccAmount;

        // Check fair usage (can't exceed 2x contribution in a day)
        // (Implementation depends on time tracking)
    }

    /**
     * @dev Report uptime violation
     */
    function reportUptimeViolation(
        string memory circleId,
        address member,
        uint256 actualUptime  // Basis points
    ) external {
        Circle storage circle = circles[circleId];
        require(actualUptime < circle.minUptime, "No violation");

        emit UptimeViolation(circleId, member, actualUptime);

        // Penalty logic (e.g., reduce member's CC allocation)
        // Or trigger vote to remove member
    }

    /**
     * @dev Vote to remove a member (2/3 majority required)
     */
    function voteRemoveMember(
        string memory circleId,
        address memberToRemove,
        string memory reason
    ) external {
        // Voting implementation
        // Requires 2/3 of members to approve
        // If approved, set member.active = false

        emit MemberRemoved(circleId, memberToRemove, reason);
    }
}
```

---

## Failover and Reliability

### The Problem: What if Someone's Machine Goes Down?

**Scenario:**
```
3-person circle: A (US), B (UK), C (Singapore)

9:00am GMT: Developer B starts work, but their machine crashed overnight
Developer B needs compute NOW, but primary machine is down

Options:
1. Wait for B to fix machine (could take hours)
2. Use A's or C's machine as backup
3. Fail over to marketplace (rent from non-circle member)
```

### Solution 1: Buddy Failover System

**Concept:** Every circle member has a designated "buddy" whose machine serves as backup.

**Configuration:**
```
Circle of 3:
- Member A's buddy → Member B (first backup) → Member C (second backup)
- Member B's buddy → Member C (first backup) → Member A (second backup)
- Member C's buddy → Member A (first backup) → Member B (second backup)

Circle of 4:
- Members paired: (A↔B) and (C↔D)
- If A fails, B is backup (and vice versa)
- If both A+B fail, use C or D
```

**Automatic Failover Process:**
```
1. Member B tries to start work session at 9:00am GMT
2. Platform pings B's machine: TIMEOUT (machine offline)
3. Platform checks B's buddy (Member C):
   - C's machine online: ✓
   - C's primary slot (9:00am SGT = 1:00am GMT): Not active ✓
   - C's machine available: ✓
4. Platform automatically migrates B's session to C's machine
5. B is notified: "Your machine is offline. Failover to Singapore server active."
6. B works normally on C's machine while fixing their own
```

**Cost Handling:**
```
Failover is covered by circle agreement (no extra cost to user)

CC Accounting:
- B still "spends" 1.0 CC/hour (their normal rate)
- C "earns" 1.0 CC/hour (providing backup)
- Platform credits C with uptime bonus for reliability
```

### Solution 2: Checkpoint and Migration

**For Long-Running Jobs:**

```python
# Checkpoint system (using DMTCP or application-level)
def handle_failover(job_id, source_machine, destination_machine):
    """
    Migrate a running job from failed machine to backup.

    Steps:
    1. Detect failure (health check timeout)
    2. Load last checkpoint from shared storage
    3. Spin up replacement machine
    4. Restore job state from checkpoint
    5. Resume execution

    Downtime: <60 seconds (vs. hours of re-running job)
    """

    # 1. Detect failure
    if not source_machine.health_check():
        logger.warning(f"Machine {source_machine.id} is offline")

        # 2. Find backup machine
        circle = get_circle(job.circle_id)
        backup_machine = circle.get_buddy_machine(source_machine.id)

        if not backup_machine or not backup_machine.health_check():
            # Buddy also offline, find any available machine in circle
            backup_machine = circle.get_any_available_machine()

        if not backup_machine:
            # No circle machines available, fail over to marketplace
            backup_machine = marketplace.find_similar_machine(
                source_machine.specs,
                max_premium=1.5  # Up to 1.5x cost acceptable
            )

        # 3. Load checkpoint
        checkpoint_path = f"s3://checkpoints/{job_id}/latest"
        checkpoint_data = load_checkpoint(checkpoint_path)

        # 4. Spin up on backup machine
        logger.info(f"Migrating job {job_id} to {backup_machine.id}")
        backup_machine.load_checkpoint(checkpoint_data)

        # 5. Resume
        backup_machine.resume_job(job_id)

        # Notify user
        notify_user(job.user_id, {
            "type": "failover",
            "job_id": job_id,
            "original_machine": source_machine.id,
            "backup_machine": backup_machine.id,
            "downtime_seconds": time.time() - failure_detected_at
        })
```

### Solution 3: Redundant Execution (Enterprise Circles)

**For Critical Workloads:**

```
Run job on 2-3 machines simultaneously
- Primary machine: Full-speed execution
- Shadow machines: Checkpoint-only mode (lower resource usage)

If primary fails:
- Shadow machine instantly promotes to primary
- Zero downtime, zero data loss

Cost:
- Primary: 1.0 CC/hour
- Shadow: 0.2 CC/hour each
- Total: 1.4 CC/hour for 2-machine redundancy

Use case: Mission-critical ML training, prod workloads
```

---

## Pricing and Cost Savings

### Cost Comparison Models

#### Solo Ownership (Baseline)
```
Hardware: $5,000 RTX 4090 workstation
Usage: 8 hours/day, 5 days/week = 2,080 hours/year
Cost per hour: $5,000 / 2,080 = $2.40/hour
Annual cost: $5,000 (one-time) + $500 (electricity/maintenance) = $5,500

Idle time: 16 hours/day × 365 days = 5,840 hours/year wasted
Utilization: 2,080 / 8,760 = 23.7%
```

#### 3-Person Compute Circle
```
Hardware contribution: $5,000 (same as solo)
Shared pool: 3 machines × 8 hours/day = 24 machine-hours/day available
Your allocation: 8 machine-hours/day (same work schedule)

But now you can use:
- Your machine (8 hours)
- Partner 1's machine (8 hours if needed)
- Partner 2's machine (8 hours if needed)
- Total potential: 24 hours/day of compute access

Cost per equivalent machine:
- $5,000 / 3 machines = $1,667 per machine
- Savings: $3,333 (66% reduction)

Annual cost: $1,667 (hardware) + $500 (utilities) = $2,167
Utilization: 24 hours used / 24 hours available = 100%
```

#### Savings Calculator

```python
def calculate_circle_savings(
    hardware_cost,
    annual_maintenance,
    work_hours_per_day,
    circle_size,
    machine_count=None
):
    """
    Calculate cost savings from joining a compute circle.

    Args:
        hardware_cost: Initial cost of hardware ($)
        annual_maintenance: Electricity, repairs, etc. ($)
        work_hours_per_day: How many hours you work per day
        circle_size: Number of people in circle
        machine_count: Number of machines (default: equal to circle_size)

    Returns:
        Dictionary with cost analysis
    """

    if machine_count is None:
        machine_count = circle_size

    # Solo ownership costs
    solo_total_cost = hardware_cost + annual_maintenance
    solo_utilization = (work_hours_per_day * 365) / (24 * 365)
    solo_cost_per_hour = solo_total_cost / (work_hours_per_day * 365)

    # Circle costs
    circle_hardware_share = hardware_cost / circle_size
    circle_maintenance_share = annual_maintenance / circle_size
    circle_total_cost = circle_hardware_share + circle_maintenance_share

    circle_available_hours = machine_count * work_hours_per_day * 365
    circle_utilization = (work_hours_per_day * 365) / circle_available_hours
    circle_cost_per_hour = circle_total_cost / (work_hours_per_day * 365)

    # Calculate savings
    annual_savings = solo_total_cost - circle_total_cost
    savings_percentage = (annual_savings / solo_total_cost) * 100

    # Effective multiplier (how many machines you have access to)
    effective_multiplier = machine_count

    return {
        "solo": {
            "total_cost": solo_total_cost,
            "cost_per_hour": solo_cost_per_hour,
            "utilization": solo_utilization
        },
        "circle": {
            "total_cost": circle_total_cost,
            "cost_per_hour": circle_cost_per_hour,
            "utilization": circle_utilization,
            "machine_access": machine_count
        },
        "savings": {
            "annual_amount": annual_savings,
            "percentage": savings_percentage,
            "effective_multiplier": f"{effective_multiplier}x hardware"
        }
    }


# Example: RTX 4090 Workstation
result = calculate_circle_savings(
    hardware_cost=5000,
    annual_maintenance=500,
    work_hours_per_day=8,
    circle_size=3
)

print(result)
# Output:
# {
#   "solo": {
#     "total_cost": 5500,
#     "cost_per_hour": 1.88,
#     "utilization": 0.333
#   },
#   "circle": {
#     "total_cost": 1833,
#     "cost_per_hour": 0.63,
#     "utilization": 0.111,
#     "machine_access": 3
#   },
#   "savings": {
#     "annual_amount": 3667,
#     "percentage": 66.7,
#     "effective_multiplier": "3x hardware"
#   }
# }
```

### Dynamic Pricing for Circle Members

```python
# Circle members get discounted rates vs marketplace rates

BASE_RATE = 1.0  # CC per hour for reference machine

def calculate_circle_member_rate(slot_type, circle_tenure_months):
    """
    Calculate CC rate for circle members.

    Circle members pay LESS than marketplace users as a loyalty benefit.
    """

    # Base rate by slot type
    if slot_type == "primary":
        rate = 0.0  # Own machine, free
    elif slot_type == "secondary":
        rate = BASE_RATE * 0.9  # 10% discount vs marketplace
    elif slot_type == "spot":
        rate = BASE_RATE * 0.7  # 30% discount vs marketplace

    # Loyalty discount (long-term circles get better rates)
    if circle_tenure_months >= 24:
        rate *= 0.9  # Additional 10% off
    elif circle_tenure_months >= 12:
        rate *= 0.95  # Additional 5% off

    return rate
```

---

## Implementation Roadmap

### Phase 1: Manual Circles (Months 1-6)

**Goal:** Validate concept with early adopters

**Features:**
- Manual circle formation (users find partners via forum/Discord)
- Basic time slot calendar (shared Google Calendar)
- Honor system for uptime commitments
- Manual CC accounting (spreadsheet tracking)

**Metrics:**
- 10-20 circles formed
- 30-60 active users
- Gather feedback on pain points

### Phase 2: Automated Matching (Months 7-12)

**Goal:** Scale with algorithmic matching

**Features:**
- Matching algorithm MVP (pseudocode above)
- Automated reservation system (database-backed)
- CC escrow for circle transactions
- Basic failover (manual intervention)

**Metrics:**
- 100+ circles formed
- 300+ active users
- 90%+ user satisfaction with matches

### Phase 3: Advanced Reliability (Months 13-18)

**Goal:** Enterprise-grade uptime

**Features:**
- Automatic failover with DMTCP checkpoints
- Buddy system implementation
- SLA enforcement (automatic credits)
- Redundant execution mode

**Metrics:**
- 99.9% uptime across all circles
- <60 second failover times
- 500+ circles, 1,500+ users

### Phase 4: Ecosystem Expansion (Months 19+)

**Goal:** Beyond compute circles

**Features:**
- Compute futures (book circles months in advance)
- Multi-tier circles (mix of hardware classes)
- Enterprise circles (8+ members)
- API for programmatic circle management

**Metrics:**
- 1,000+ circles
- 10,000+ users
- $1M+ monthly CC transactions

---

## Conclusion

Timezone arbitrage transforms Compute Capital from a payment mechanism into a **resource optimization system**. By enabling compute circles, the marketplace achieves:

1. **100% hardware utilization** (vs 20-30% solo)
2. **66% cost reduction** per user ($1,667 vs $5,000)
3. **3x hardware access** for same investment
4. **Built-in redundancy** (failover to buddies)
5. **Natural liquidity** (always someone needing compute)

**Key Success Factors:**
- **Excellent matching algorithm** (get timezone/hardware compatibility right)
- **Robust failover** (can't have downtime kill trust)
- **Clear contracts** (legal framework for multi-party agreements)
- **Fair pricing** (performance-weighted CC prevents exploitation)

**See Also:**
- `compute-capital-currency-design.md` - How CC enables this economically
- `internal-marketplace-design.md` - Trading mechanics between circles
- `circulation-incentives.md` - Keeping circles active and engaged

---

**Document End**
