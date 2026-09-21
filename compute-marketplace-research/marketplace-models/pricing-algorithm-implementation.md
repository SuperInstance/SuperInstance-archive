# Dynamic Pricing Algorithm Implementation

## Executive Summary

This document provides comprehensive implementation details for a dynamic pricing engine for the compute marketplace platform. It includes algorithm design, pseudocode, real-time calculation engine, weighting factors, code examples in Python and JavaScript, caching strategies, and optional ML integration.

**Pricing Objective**: Maximize marketplace efficiency by balancing supply and demand while ensuring fair pricing for both providers and buyers.

---

## Table of Contents

1. [Pricing Strategy Overview](#pricing-strategy-overview)
2. [Algorithm Design](#algorithm-design)
3. [Factors and Weighting](#factors-and-weighting)
4. [Real-Time Calculation Engine](#real-time-calculation-engine)
5. [Code Examples](#code-examples)
6. [Caching Strategy](#caching-strategy)
7. [ML Integration](#ml-integration-optional)
8. [Testing and Validation](#testing-and-validation)

---

## Pricing Strategy Overview

### Pricing Models Comparison

| Model | Description | Pros | Cons | Best For |
|-------|-------------|------|------|----------|
| **Fixed Pricing** | Provider sets price, never changes | Simple, predictable | Inefficient, misses opportunities | Early stage, low volume |
| **Dynamic Pricing** | Price adjusts based on demand, supply, time | Revenue optimization, market efficiency | Complex, requires data | Mature marketplace |
| **Auction-Based** | Buyers bid for resources | Price discovery, high revenue potential | Unpredictable for buyers | High-value, scarce resources |
| **Surge Pricing** | Price multiplier during high demand | Balances supply/demand | Customer backlash | Peak times only |
| **Tiered Pricing** | Discount for longer bookings | Encourages commitment | Less flexible | Predictable workloads |

**Recommendation**: **Dynamic Pricing with Tiered Discounts** for optimal balance.

### Dynamic Pricing Goals

```
1. Maximize utilization (reduce idle resources)
2. Maximize revenue (capture willingness to pay)
3. Balance supply and demand
4. Remain competitive with market rates
5. Reward provider reputation and performance
6. Incentivize longer bookings
```

---

## Algorithm Design

### Base Pricing Formula

```
Final Price = Base Price × Demand Factor × Supply Factor × Time Factor × Reputation Factor × Seasonal Factor

With constraints:
  - Final Price >= Floor Price (minimum acceptable price)
  - Final Price <= Ceiling Price (maximum reasonable price)
```

### Pseudocode (High-Level)

```
function calculateDynamicPrice(resource, booking_parameters):
    # 1. Get base price from provider
    base_price = resource.price_per_hour

    # 2. Calculate adjustment factors (each in range [0.5, 2.0])
    demand_factor = calculateDemandFactor(resource, booking_parameters)
    supply_factor = calculateSupplyFactor(resource.type, resource.location)
    time_factor = calculateTimeFactor(booking_parameters.start_time)
    reputation_factor = calculateReputationFactor(resource)
    duration_factor = calculateDurationFactor(booking_parameters.duration)
    seasonal_factor = calculateSeasonalFactor(current_time)

    # 3. Apply factors
    adjusted_price = base_price
        × demand_factor
        × supply_factor
        × time_factor
        × reputation_factor
        × duration_factor
        × seasonal_factor

    # 4. Apply constraints
    floor_price = base_price × 0.7  # Never drop below 70% of base
    ceiling_price = base_price × 3.0  # Never exceed 3x base

    final_price = clamp(adjusted_price, floor_price, ceiling_price)

    # 5. Round to reasonable precision
    return round(final_price, 2)
```

### Detailed Algorithm Flow

```
┌─────────────────────────────────────────────┐
│         Input: Resource + Booking           │
│         - Resource ID                       │
│         - Start time                        │
│         - Duration                          │
│         - Location                          │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│    Step 1: Retrieve Base Price              │
│    - Provider's set price                   │
│    - Market average for resource type       │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│    Step 2: Calculate Demand Factor          │
│    - Current booking rate                   │
│    - Historical demand patterns             │
│    - Time-of-day demand                     │
│    - Competitor bookings                    │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│    Step 3: Calculate Supply Factor          │
│    - Available similar resources            │
│    - Geographic availability                │
│    - Resource type scarcity                 │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│    Step 4: Calculate Time Factor            │
│    - Lead time (how far in advance)         │
│    - Time of day (peak vs off-peak)         │
│    - Day of week (weekday vs weekend)       │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│    Step 5: Calculate Reputation Factor      │
│    - Resource rating                        │
│    - Provider rating                        │
│    - Uptime history                         │
│    - Number of completed bookings           │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│    Step 6: Calculate Duration Factor        │
│    - Discount for longer bookings           │
│    - Premium for very short bookings        │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│    Step 7: Apply Factors & Constraints      │
│    - Multiply all factors                   │
│    - Apply floor and ceiling                │
│    - Round to precision                     │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│         Output: Dynamic Price               │
│         - Final price per hour              │
│         - Breakdown of factors              │
│         - Total cost for booking            │
└─────────────────────────────────────────────┘
```

---

## Factors and Weighting

### 1. Demand Factor (Weight: 30%)

**Range**: [0.7, 1.8]

**Formula**:
```
demand_factor = 1.0 + (current_demand_ratio - 0.5) × 1.6

where:
  current_demand_ratio = active_bookings / total_capacity
  clamped to [0, 1]

Examples:
  - 20% demand → factor = 0.76
  - 50% demand → factor = 1.0
  - 80% demand → factor = 1.48
  - 95% demand → factor = 1.72
```

**Implementation**:
```python
def calculate_demand_factor(resource_type: str, location: str, time_window: tuple) -> float:
    """
    Calculate demand factor based on current and predicted bookings.

    Args:
        resource_type: Type of resource (gpu, cpu, etc.)
        location: Geographic region
        time_window: (start_time, end_time) for the booking

    Returns:
        Demand factor in range [0.7, 1.8]
    """
    # Query active bookings in the same time window
    active_bookings = db.query("""
        SELECT COUNT(*) as count
        FROM bookings
        WHERE resource_id IN (
            SELECT id FROM resources
            WHERE resource_type = %s AND location_region = %s
        )
        AND status IN ('confirmed', 'active')
        AND (start_time, end_time) OVERLAPS (%s, %s)
    """, (resource_type, location, time_window[0], time_window[1]))

    # Query total capacity
    total_capacity = db.query("""
        SELECT COUNT(*) as count
        FROM resources
        WHERE resource_type = %s
        AND location_region = %s
        AND availability_status = 'available'
    """, (resource_type, location))

    # Calculate demand ratio
    if total_capacity == 0:
        return 1.0  # Neutral if no data

    demand_ratio = min(active_bookings / total_capacity, 1.0)

    # Apply formula
    demand_factor = 1.0 + (demand_ratio - 0.5) * 1.6

    # Clamp to range
    return max(0.7, min(1.8, demand_factor))
```

### 2. Supply Factor (Weight: 25%)

**Range**: [0.8, 1.5]

**Formula**:
```
supply_factor = 2.0 - supply_ratio

where:
  supply_ratio = available_resources / average_available_resources
  clamped to [0.5, 1.2]

Examples:
  - 120% of avg supply → factor = 0.8 (price decrease)
  - 100% of avg supply → factor = 1.0 (neutral)
  - 70% of avg supply → factor = 1.3 (price increase)
  - 50% of avg supply → factor = 1.5 (max price increase)
```

**Implementation**:
```javascript
async function calculateSupplyFactor(resourceType, location) {
  // Current available resources
  const currentSupply = await db.query(`
    SELECT COUNT(*) as count
    FROM resources
    WHERE resource_type = $1
      AND location_region = $2
      AND availability_status = 'available'
      AND deleted_at IS NULL
  `, [resourceType, location]);

  // Average supply over past 30 days
  const avgSupply = await db.query(`
    SELECT AVG(daily_count) as avg_count
    FROM (
      SELECT DATE(created_at) as date, COUNT(*) as daily_count
      FROM resources
      WHERE resource_type = $1
        AND location_region = $2
        AND created_at >= NOW() - INTERVAL '30 days'
      GROUP BY DATE(created_at)
    ) daily_stats
  `, [resourceType, location]);

  if (!avgSupply || avgSupply === 0) {
    return 1.0; // Neutral if no historical data
  }

  const supplyRatio = currentSupply / avgSupply;
  const clampedRatio = Math.max(0.5, Math.min(1.2, supplyRatio));

  const supplyFactor = 2.0 - clampedRatio;

  return Math.max(0.8, Math.min(1.5, supplyFactor));
}
```

### 3. Time Factor (Weight: 20%)

**Range**: [0.8, 1.3]

**Components**:
- Lead time (how far in advance): Longer lead time → lower price
- Time of day: Peak hours (9 AM - 6 PM) → higher price
- Day of week: Weekdays → higher price

**Formula**:
```
time_factor = lead_time_factor × time_of_day_factor × day_of_week_factor

lead_time_factor:
  - < 1 hour:   1.3 (last-minute premium)
  - 1-6 hours:  1.2
  - 6-24 hours: 1.1
  - 1-3 days:   1.0
  - 3-7 days:   0.95
  - > 7 days:   0.9 (early booking discount)

time_of_day_factor:
  - Peak hours (9 AM - 6 PM):    1.1
  - Off-peak hours:              0.95

day_of_week_factor:
  - Weekdays (Mon-Fri):  1.05
  - Weekends (Sat-Sun):  0.95
```

**Implementation**:
```python
from datetime import datetime, timedelta

def calculate_time_factor(start_time: datetime) -> float:
    """Calculate time-based pricing factor."""
    now = datetime.now()

    # Lead time factor
    lead_time = start_time - now
    if lead_time < timedelta(hours=1):
        lead_time_factor = 1.3
    elif lead_time < timedelta(hours=6):
        lead_time_factor = 1.2
    elif lead_time < timedelta(hours=24):
        lead_time_factor = 1.1
    elif lead_time < timedelta(days=3):
        lead_time_factor = 1.0
    elif lead_time < timedelta(days=7):
        lead_time_factor = 0.95
    else:
        lead_time_factor = 0.9

    # Time of day factor (peak vs off-peak)
    hour = start_time.hour
    if 9 <= hour < 18:  # 9 AM - 6 PM
        time_of_day_factor = 1.1
    else:
        time_of_day_factor = 0.95

    # Day of week factor
    weekday = start_time.weekday()
    if weekday < 5:  # Monday = 0, Friday = 4
        day_of_week_factor = 1.05
    else:
        day_of_week_factor = 0.95

    # Combine factors
    time_factor = lead_time_factor * time_of_day_factor * day_of_week_factor

    # Clamp to range
    return max(0.8, min(1.3, time_factor))
```

### 4. Reputation Factor (Weight: 15%)

**Range**: [0.9, 1.2]

**Formula**:
```
reputation_factor = 0.9 + (normalized_reputation × 0.3)

where:
  normalized_reputation = (rating_avg / 5.0) × (min(completed_bookings, 100) / 100)

Examples:
  - 5.0 rating, 100+ bookings → factor = 1.2
  - 4.0 rating, 50 bookings → factor = 1.02
  - 3.0 rating, 10 bookings → factor = 0.94
  - New resource (no ratings) → factor = 1.0
```

**Implementation**:
```javascript
function calculateReputationFactor(resource) {
  if (resource.rating_count === 0) {
    return 1.0; // Neutral for new resources
  }

  // Normalize rating (0-5 scale to 0-1)
  const ratingScore = resource.rating_avg / 5.0;

  // Normalize booking count (cap at 100)
  const bookingScore = Math.min(resource.total_bookings, 100) / 100;

  // Combine scores
  const normalizedReputation = ratingScore * bookingScore;

  // Apply formula
  const reputationFactor = 0.9 + (normalizedReputation * 0.3);

  return Math.max(0.9, Math.min(1.2, reputationFactor));
}
```

### 5. Duration Factor (Weight: 10%)

**Range**: [0.85, 1.15]

**Formula**:
```
duration_factor = 1.0 - (duration_discount_rate × log(duration_hours))

where:
  duration_discount_rate = 0.05
  clamped to [0.85, 1.15]

Examples:
  - 1 hour:    factor = 1.0 (no discount)
  - 4 hours:   factor = 0.93 (7% discount)
  - 24 hours:  factor = 0.84 → clamped to 0.85 (15% discount)
  - 168 hours: factor = 0.74 → clamped to 0.85 (15% discount)
```

**Implementation**:
```python
import math

def calculate_duration_factor(duration_hours: float) -> float:
    """Calculate discount for longer bookings."""
    if duration_hours <= 1:
        return 1.0  # No discount for very short bookings

    # Logarithmic discount (diminishing returns)
    duration_discount_rate = 0.05
    duration_factor = 1.0 - (duration_discount_rate * math.log(duration_hours))

    # Clamp to range
    return max(0.85, min(1.15, duration_factor))

# Alternative: Tiered discounts
def calculate_duration_factor_tiered(duration_hours: float) -> float:
    """Tiered discount structure."""
    if duration_hours < 1:
        return 1.1  # Premium for very short bookings
    elif duration_hours < 4:
        return 1.0  # No discount
    elif duration_hours < 24:
        return 0.95  # 5% discount
    elif duration_hours < 168:  # 1 week
        return 0.9  # 10% discount
    elif duration_hours < 720:  # 1 month
        return 0.85  # 15% discount
    else:
        return 0.8  # 20% discount for very long bookings
```

### 6. Seasonal Factor (Optional)

**Range**: [0.95, 1.15]

**Use Cases**:
- Tax season (accounting software demand)
- ML conference season (GPU demand)
- Year-end (budget spending)
- Summer (lower enterprise demand)

**Implementation**:
```python
def calculate_seasonal_factor(resource_type: str, current_date: datetime) -> float:
    """Calculate seasonal demand adjustments."""

    # Define seasonal patterns by resource type
    seasonal_patterns = {
        'gpu': {
            'high_demand_months': [9, 10, 11],  # Sep, Oct, Nov (ML conference season)
            'low_demand_months': [6, 7, 8],     # Jun, Jul, Aug (summer slowdown)
        },
        'cpu': {
            'high_demand_months': [12, 3, 4],   # Dec, Mar, Apr (year-end, tax season)
            'low_demand_months': [7, 8],        # Jul, Aug
        }
    }

    month = current_date.month

    if resource_type in seasonal_patterns:
        pattern = seasonal_patterns[resource_type]

        if month in pattern['high_demand_months']:
            return 1.15  # 15% increase
        elif month in pattern['low_demand_months']:
            return 0.95  # 5% decrease

    return 1.0  # Neutral
```

---

## Real-Time Calculation Engine

### Architecture

```
┌─────────────────────────────────────────────────┐
│              API Request                        │
│  GET /api/v1/pricing/calculate                  │
│  {                                              │
│    resourceId: "uuid",                          │
│    startTime: "2025-02-01T10:00:00Z",           │
│    duration: 4                                  │
│  }                                              │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│         Pricing Service (Node.js)               │
│  - Fetch resource details                       │
│  - Calculate factors                            │
│  - Apply formula                                │
└──────────────────┬──────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
┌────────────┐ ┌────────┐ ┌──────────┐
│ PostgreSQL │ │ Redis  │ │ Analytics│
│ (Resource) │ │ (Cache)│ │ Service  │
└────────────┘ └────────┘ └──────────┘
```

### Complete Implementation (Node.js + TypeScript)

```typescript
// src/modules/pricing/pricing.service.ts
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { RedisService } from '../redis/redis.service';
import { Resource } from '../resources/entities/resource.entity';

interface PricingInput {
  resourceId: string;
  startTime: Date;
  endTime: Date;
  duration: number; // hours
}

interface PricingResult {
  basePrice: number;
  adjustedPrice: number;
  totalCost: number;
  factors: {
    demand: number;
    supply: number;
    time: number;
    reputation: number;
    duration: number;
    seasonal: number;
  };
  breakdown: string[];
}

@Injectable()
export class PricingService {
  constructor(
    @InjectRepository(Resource)
    private resourceRepository: Repository<Resource>,
    private redisService: RedisService,
  ) {}

  async calculateDynamicPrice(input: PricingInput): Promise<PricingResult> {
    // 1. Fetch resource details
    const resource = await this.resourceRepository.findOne({
      where: { id: input.resourceId },
      relations: ['provider'],
    });

    if (!resource) {
      throw new Error('Resource not found');
    }

    const basePrice = resource.price_per_hour;

    // 2. Calculate all factors (in parallel for performance)
    const [
      demandFactor,
      supplyFactor,
      timeFactor,
      reputationFactor,
      durationFactor,
      seasonalFactor,
    ] = await Promise.all([
      this.calculateDemandFactor(resource, input),
      this.calculateSupplyFactor(resource),
      this.calculateTimeFactor(input.startTime),
      this.calculateReputationFactor(resource),
      this.calculateDurationFactor(input.duration),
      this.calculateSeasonalFactor(resource.resource_type),
    ]);

    // 3. Apply factors
    let adjustedPrice = basePrice
      * demandFactor
      * supplyFactor
      * timeFactor
      * reputationFactor
      * durationFactor
      * seasonalFactor;

    // 4. Apply constraints (floor and ceiling)
    const floorPrice = basePrice * 0.7;
    const ceilingPrice = basePrice * 3.0;
    adjustedPrice = Math.max(floorPrice, Math.min(ceilingPrice, adjustedPrice));

    // 5. Round to 2 decimal places
    adjustedPrice = Math.round(adjustedPrice * 100) / 100;

    // 6. Calculate total cost
    const totalCost = adjustedPrice * input.duration;

    // 7. Generate breakdown
    const breakdown = [
      `Base price: $${basePrice.toFixed(2)}/hour`,
      `Demand factor: ${demandFactor.toFixed(2)}x (${((demandFactor - 1) * 100).toFixed(0)}%)`,
      `Supply factor: ${supplyFactor.toFixed(2)}x (${((supplyFactor - 1) * 100).toFixed(0)}%)`,
      `Time factor: ${timeFactor.toFixed(2)}x (${((timeFactor - 1) * 100).toFixed(0)}%)`,
      `Reputation factor: ${reputationFactor.toFixed(2)}x (${((reputationFactor - 1) * 100).toFixed(0)}%)`,
      `Duration factor: ${durationFactor.toFixed(2)}x (${((durationFactor - 1) * 100).toFixed(0)}%)`,
      `Seasonal factor: ${seasonalFactor.toFixed(2)}x (${((seasonalFactor - 1) * 100).toFixed(0)}%)`,
      `Adjusted price: $${adjustedPrice.toFixed(2)}/hour`,
      `Total cost (${input.duration}h): $${totalCost.toFixed(2)}`,
    ];

    return {
      basePrice,
      adjustedPrice,
      totalCost,
      factors: {
        demand: demandFactor,
        supply: supplyFactor,
        time: timeFactor,
        reputation: reputationFactor,
        duration: durationFactor,
        seasonal: seasonalFactor,
      },
      breakdown,
    };
  }

  private async calculateDemandFactor(
    resource: Resource,
    input: PricingInput,
  ): Promise<number> {
    // Try cache first
    const cacheKey = `demand:${resource.resource_type}:${resource.location_region}`;
    const cached = await this.redisService.get(cacheKey);

    if (cached) {
      return parseFloat(cached);
    }

    // Calculate demand
    const activeBookings = await this.resourceRepository.query(`
      SELECT COUNT(*) as count
      FROM bookings
      WHERE resource_id IN (
        SELECT id FROM resources
        WHERE resource_type = $1 AND location_region = $2
      )
      AND status IN ('confirmed', 'active')
      AND (start_time, end_time) OVERLAPS ($3, $4)
    `, [resource.resource_type, resource.location_region, input.startTime, input.endTime]);

    const totalCapacity = await this.resourceRepository.count({
      where: {
        resource_type: resource.resource_type,
        location_region: resource.location_region,
        availability_status: 'available',
      },
    });

    const demandRatio = totalCapacity > 0 ? Math.min(activeBookings[0].count / totalCapacity, 1.0) : 0;
    const demandFactor = Math.max(0.7, Math.min(1.8, 1.0 + (demandRatio - 0.5) * 1.6));

    // Cache for 5 minutes
    await this.redisService.setEx(cacheKey, 300, demandFactor.toString());

    return demandFactor;
  }

  private async calculateSupplyFactor(resource: Resource): Promise<number> {
    const cacheKey = `supply:${resource.resource_type}:${resource.location_region}`;
    const cached = await this.redisService.get(cacheKey);

    if (cached) {
      return parseFloat(cached);
    }

    const currentSupply = await this.resourceRepository.count({
      where: {
        resource_type: resource.resource_type,
        location_region: resource.location_region,
        availability_status: 'available',
      },
    });

    const avgSupply = await this.resourceRepository.query(`
      SELECT AVG(daily_count) as avg_count
      FROM (
        SELECT DATE(created_at) as date, COUNT(*) as daily_count
        FROM resources
        WHERE resource_type = $1
          AND location_region = $2
          AND created_at >= NOW() - INTERVAL '30 days'
        GROUP BY DATE(created_at)
      ) daily_stats
    `, [resource.resource_type, resource.location_region]);

    const avgCount = avgSupply[0]?.avg_count || currentSupply;
    const supplyRatio = avgCount > 0 ? currentSupply / avgCount : 1.0;
    const clampedRatio = Math.max(0.5, Math.min(1.2, supplyRatio));
    const supplyFactor = Math.max(0.8, Math.min(1.5, 2.0 - clampedRatio));

    // Cache for 10 minutes
    await this.redisService.setEx(cacheKey, 600, supplyFactor.toString());

    return supplyFactor;
  }

  private calculateTimeFactor(startTime: Date): number {
    const now = new Date();
    const leadTimeMs = startTime.getTime() - now.getTime();
    const leadTimeHours = leadTimeMs / (1000 * 60 * 60);

    // Lead time factor
    let leadTimeFactor: number;
    if (leadTimeHours < 1) {
      leadTimeFactor = 1.3;
    } else if (leadTimeHours < 6) {
      leadTimeFactor = 1.2;
    } else if (leadTimeHours < 24) {
      leadTimeFactor = 1.1;
    } else if (leadTimeHours < 72) {
      leadTimeFactor = 1.0;
    } else if (leadTimeHours < 168) {
      leadTimeFactor = 0.95;
    } else {
      leadTimeFactor = 0.9;
    }

    // Time of day factor
    const hour = startTime.getHours();
    const timeOfDayFactor = (hour >= 9 && hour < 18) ? 1.1 : 0.95;

    // Day of week factor
    const dayOfWeek = startTime.getDay();
    const dayOfWeekFactor = (dayOfWeek >= 1 && dayOfWeek <= 5) ? 1.05 : 0.95;

    const timeFactor = leadTimeFactor * timeOfDayFactor * dayOfWeekFactor;

    return Math.max(0.8, Math.min(1.3, timeFactor));
  }

  private calculateReputationFactor(resource: Resource): number {
    if (resource.rating_count === 0) {
      return 1.0;
    }

    const ratingScore = resource.rating_avg / 5.0;
    const bookingScore = Math.min(resource.total_bookings, 100) / 100;
    const normalizedReputation = ratingScore * bookingScore;
    const reputationFactor = 0.9 + (normalizedReputation * 0.3);

    return Math.max(0.9, Math.min(1.2, reputationFactor));
  }

  private calculateDurationFactor(durationHours: number): number {
    if (durationHours < 1) {
      return 1.1; // Premium for very short bookings
    } else if (durationHours < 4) {
      return 1.0;
    } else if (durationHours < 24) {
      return 0.95;
    } else if (durationHours < 168) {
      return 0.9;
    } else if (durationHours < 720) {
      return 0.85;
    } else {
      return 0.8;
    }
  }

  private calculateSeasonalFactor(resourceType: string): number {
    const now = new Date();
    const month = now.getMonth() + 1; // JavaScript months are 0-indexed

    const seasonalPatterns: Record<string, { high: number[]; low: number[] }> = {
      gpu: { high: [9, 10, 11], low: [6, 7, 8] },
      cpu: { high: [12, 3, 4], low: [7, 8] },
    };

    const pattern = seasonalPatterns[resourceType];

    if (pattern) {
      if (pattern.high.includes(month)) {
        return 1.15;
      } else if (pattern.low.includes(month)) {
        return 0.95;
      }
    }

    return 1.0;
  }
}
```

### API Controller

```typescript
// src/modules/pricing/pricing.controller.ts
import { Controller, Post, Body, UseGuards } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse } from '@nestjs/swagger';
import { PricingService } from './pricing.service';

class CalculatePriceDto {
  resourceId: string;
  startTime: Date;
  endTime: Date;
  duration: number;
}

@ApiTags('pricing')
@Controller('api/v1/pricing')
export class PricingController {
  constructor(private readonly pricingService: PricingService) {}

  @Post('calculate')
  @ApiOperation({ summary: 'Calculate dynamic price for a booking' })
  @ApiResponse({ status: 200, description: 'Price calculated successfully' })
  async calculatePrice(@Body() dto: CalculatePriceDto) {
    return this.pricingService.calculateDynamicPrice(dto);
  }
}
```

---

## Caching Strategy

### Multi-Layer Caching

```
┌─────────────────────────────────────────┐
│   Layer 1: Application Cache (In-Memory)│
│   - TTL: 1 minute                       │
│   - Scope: Single server                │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│   Layer 2: Redis Cache (Distributed)    │
│   - TTL: 5-10 minutes                   │
│   - Scope: All servers                  │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│   Layer 3: Database (Source of Truth)   │
│   - Always fresh                        │
└─────────────────────────────────────────┘
```

### Cache Keys and TTLs

```javascript
// Cache key structure
const cacheKeys = {
  demand: `pricing:demand:${resourceType}:${location}`,      // TTL: 5 min
  supply: `pricing:supply:${resourceType}:${location}`,      // TTL: 10 min
  resource: `pricing:resource:${resourceId}`,                // TTL: 15 min
  finalPrice: `pricing:final:${resourceId}:${startTime}:${duration}`, // TTL: 2 min
};

// Example caching wrapper
async function cachedCalculation(cacheKey, ttl, calculationFn) {
  // Try cache
  const cached = await redis.get(cacheKey);
  if (cached) {
    return JSON.parse(cached);
  }

  // Calculate
  const result = await calculationFn();

  // Store in cache
  await redis.setex(cacheKey, ttl, JSON.stringify(result));

  return result;
}
```

### Cache Invalidation Strategy

```javascript
// Invalidate on events
async function onBookingCreated(booking) {
  // Invalidate demand cache for this resource type/location
  const keys = await redis.keys(`pricing:demand:${booking.resourceType}:${booking.location}*`);
  if (keys.length > 0) {
    await redis.del(...keys);
  }
}

async function onResourceUpdated(resource) {
  // Invalidate specific resource cache
  await redis.del(`pricing:resource:${resource.id}`);

  // Invalidate supply cache
  await redis.del(`pricing:supply:${resource.type}:${resource.location}`);
}
```

---

## ML Integration (Optional)

### When to Use ML

```
✓ Large dataset (>100K bookings)
✓ Complex patterns (multiple variables)
✓ Predictive pricing (forecast future demand)
✓ Personalization (user-specific pricing)
✓ Anomaly detection (unusual patterns)
```

### ML Model Approach

**Model Type**: Gradient Boosting (XGBoost, LightGBM) or Neural Network

**Input Features**:
```python
features = [
    # Resource features
    'resource_type',
    'location_region',
    'cpu_cores',
    'ram_gb',
    'gpu_count',
    'gpu_model',
    'rating_avg',
    'total_bookings',

    # Temporal features
    'hour_of_day',
    'day_of_week',
    'month',
    'is_weekend',
    'is_holiday',
    'lead_time_hours',

    # Market features
    'current_demand_ratio',
    'supply_count',
    'competitor_avg_price',

    # Booking features
    'duration_hours',
    'is_repeat_customer',
]
```

**Target Variable**: `actual_booking_price` (historical)

### Training Pipeline (Python)

```python
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

# 1. Load historical bookings data
df = pd.read_sql("""
    SELECT
        b.id,
        b.price_per_hour as actual_price,
        r.resource_type,
        r.location_region,
        r.specs->>'cpu_cores' as cpu_cores,
        r.specs->>'ram_gb' as ram_gb,
        r.rating_avg,
        r.total_bookings,
        EXTRACT(HOUR FROM b.start_time) as hour_of_day,
        EXTRACT(DOW FROM b.start_time) as day_of_week,
        EXTRACT(MONTH FROM b.start_time) as month,
        b.duration_hours,
        -- Add more features
    FROM bookings b
    JOIN resources r ON b.resource_id = r.id
    WHERE b.status = 'completed'
        AND b.created_at >= NOW() - INTERVAL '1 year'
""", db_connection)

# 2. Feature engineering
df['is_weekend'] = df['day_of_week'].isin([0, 6]).astype(int)
df['is_peak_hour'] = ((df['hour_of_day'] >= 9) & (df['hour_of_day'] < 18)).astype(int)

# 3. Encode categorical features
df = pd.get_dummies(df, columns=['resource_type', 'location_region'])

# 4. Split data
X = df.drop(['id', 'actual_price'], axis=1)
y = df['actual_price']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 5. Train model
model = xgb.XGBRegressor(
    n_estimators=1000,
    learning_rate=0.01,
    max_depth=8,
    subsample=0.8,
    colsample_bytree=0.8,
    objective='reg:squarederror',
    random_state=42
)

model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    early_stopping_rounds=50,
    verbose=False
)

# 6. Evaluate
from sklearn.metrics import mean_absolute_error, r2_score

y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"MAE: ${mae:.2f}")
print(f"R² Score: {r2:.3f}")

# 7. Save model
import joblib
joblib.dump(model, 'models/pricing_model_v1.pkl')
```

### Inference (Real-Time Prediction)

```python
import joblib
import numpy as np

# Load model
model = joblib.load('models/pricing_model_v1.pkl')

def predict_price_ml(resource, booking_params):
    """Predict price using ML model."""

    # Prepare features
    features = {
        'resource_type': resource.resource_type,
        'location_region': resource.location_region,
        'cpu_cores': resource.specs.get('cpu', {}).get('cores', 0),
        'ram_gb': resource.specs.get('ram', {}).get('size_gb', 0),
        'rating_avg': resource.rating_avg,
        'total_bookings': resource.total_bookings,
        'hour_of_day': booking_params.start_time.hour,
        'day_of_week': booking_params.start_time.weekday(),
        'month': booking_params.start_time.month,
        'duration_hours': booking_params.duration,
        # ... more features
    }

    # Convert to DataFrame (required for preprocessing)
    df = pd.DataFrame([features])

    # Apply same preprocessing as training
    df = pd.get_dummies(df, columns=['resource_type', 'location_region'])

    # Ensure all columns from training are present
    # (handle missing dummy columns)
    for col in model.feature_names_in_:
        if col not in df.columns:
            df[col] = 0

    df = df[model.feature_names_in_]  # Reorder columns

    # Predict
    predicted_price = model.predict(df)[0]

    return predicted_price
```

### Hybrid Approach (Rule-Based + ML)

```python
def calculate_final_price_hybrid(resource, booking_params):
    """Combine rule-based and ML-based pricing."""

    # 1. Get rule-based price
    rule_based_price = calculate_dynamic_price(resource, booking_params)

    # 2. Get ML-based price
    ml_price = predict_price_ml(resource, booking_params)

    # 3. Blend (weighted average)
    # Give more weight to ML as more data is collected
    ml_confidence = min(resource.total_bookings / 100, 0.7)  # Max 70% ML weight

    final_price = (
        rule_based_price * (1 - ml_confidence) +
        ml_price * ml_confidence
    )

    # 4. Apply constraints
    base_price = resource.price_per_hour
    floor = base_price * 0.7
    ceiling = base_price * 3.0

    return max(floor, min(ceiling, final_price))
```

---

## Testing and Validation

### Unit Tests

```typescript
// pricing.service.spec.ts
describe('PricingService', () => {
  let service: PricingService;

  beforeEach(async () => {
    // Setup test module
  });

  describe('calculateDemandFactor', () => {
    it('should return 1.0 for 50% demand', async () => {
      // Mock 50% demand
      const factor = await service.calculateDemandFactor(/* ... */);
      expect(factor).toBeCloseTo(1.0, 1);
    });

    it('should return > 1.0 for high demand', async () => {
      // Mock 80% demand
      const factor = await service.calculateDemandFactor(/* ... */);
      expect(factor).toBeGreaterThan(1.0);
    });

    it('should return < 1.0 for low demand', async () => {
      // Mock 20% demand
      const factor = await service.calculateDemandFactor(/* ... */);
      expect(factor).toBeLessThan(1.0);
    });
  });

  describe('calculateDynamicPrice', () => {
    it('should never go below floor price', async () => {
      const result = await service.calculateDynamicPrice(/* ... */);
      expect(result.adjustedPrice).toBeGreaterThanOrEqual(result.basePrice * 0.7);
    });

    it('should never exceed ceiling price', async () => {
      const result = await service.calculateDynamicPrice(/* ... */);
      expect(result.adjustedPrice).toBeLessThanOrEqual(result.basePrice * 3.0);
    });

    it('should apply duration discount', async () => {
      const shortBooking = await service.calculateDynamicPrice({ duration: 1, /* ... */ });
      const longBooking = await service.calculateDynamicPrice({ duration: 24, /* ... */ });

      expect(longBooking.factors.duration).toBeLessThan(shortBooking.factors.duration);
    });
  });
});
```

### Integration Tests

```python
# test_pricing_integration.py
import pytest
from datetime import datetime, timedelta

def test_end_to_end_pricing(client, test_db):
    # 1. Create test resource
    resource = create_test_resource(
        resource_type='gpu',
        price_per_hour=10.0,
        rating_avg=4.5,
        total_bookings=50
    )

    # 2. Call pricing API
    response = client.post('/api/v1/pricing/calculate', json={
        'resourceId': resource.id,
        'startTime': (datetime.now() + timedelta(hours=24)).isoformat(),
        'duration': 4
    })

    assert response.status_code == 200
    data = response.json()

    # 3. Validate response
    assert 'adjustedPrice' in data
    assert 'totalCost' in data
    assert 'factors' in data

    # 4. Validate price range
    assert data['adjustedPrice'] >= resource.price_per_hour * 0.7
    assert data['adjustedPrice'] <= resource.price_per_hour * 3.0

    # 5. Validate total cost
    expected_total = data['adjustedPrice'] * 4
    assert abs(data['totalCost'] - expected_total) < 0.01
```

### A/B Testing

```javascript
// Randomly assign users to different pricing strategies
async function getPriceForUser(userId, resource, booking) {
  const userGroup = hashUserId(userId) % 100;

  if (userGroup < 50) {
    // Group A: Rule-based pricing
    return calculateDynamicPrice(resource, booking);
  } else {
    // Group B: ML-based pricing
    return predictPriceML(resource, booking);
  }
}

// Track conversions
async function trackPricingConversion(userId, priceShown, didBook) {
  await analytics.track({
    event: 'pricing_conversion',
    userId,
    properties: {
      priceShown,
      didBook,
      conversionRate: didBook ? 1 : 0,
    }
  });
}
```

---

## Conclusion

This dynamic pricing implementation provides:

1. **Multi-factor algorithm** balancing demand, supply, time, reputation, duration, and seasonal patterns
2. **Real-time calculation** with multi-layer caching for performance
3. **Flexible architecture** supporting both rule-based and ML-based approaches
4. **Production-ready code** in TypeScript/Node.js with comprehensive examples
5. **Validation and testing** strategies to ensure pricing correctness

**Key Metrics to Monitor**:
- Average price adjustment: Should be within ±20% of base price
- Conversion rate: Track booking completion by price point
- Revenue per available resource hour (RevPARH)
- Price elasticity: Measure booking volume vs price changes
- Provider satisfaction: Ensure providers are happy with earnings

**Next Steps**:
1. Deploy rule-based pricing initially
2. Collect 6-12 months of booking data
3. Train ML models with historical data
4. A/B test ML vs rule-based pricing
5. Gradually increase ML model weight based on performance

---

**Document Version**: 1.0
**Last Updated**: 2025-10-14
**Author**: Pricing Algorithm Team
