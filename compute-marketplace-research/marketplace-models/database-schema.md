# Database Schema Design: Compute Marketplace Platform

## Executive Summary

This document provides comprehensive database schema design for a compute marketplace platform, including entity-relationship diagrams, complete SQL schemas, indexing strategies, partitioning for scale, and example queries.

**Database**: PostgreSQL 15+
**Target Scale**: 1M+ users, 10M+ resources, 100M+ bookings

---

## Table of Contents

1. [Entity-Relationship Diagram](#entity-relationship-diagram)
2. [Core Tables](#core-tables)
3. [Indexing Strategy](#indexing-strategy)
4. [Partitioning for Scale](#partitioning-for-scale)
5. [Database Constraints](#database-constraints)
6. [Example Queries](#example-queries)
7. [Migration Strategy](#migration-strategy)
8. [Performance Optimization](#performance-optimization)

---

## Entity-Relationship Diagram

### High-Level ER Diagram (Text Format)

```
┌──────────────┐
│    USERS     │
│──────────────│
│ PK id        │
│    email     │
│    password  │
│    role      │
│    created_at│
└───────┬──────┘
        │
        │ 1:N (provider)
        │
┌───────▼──────────┐         ┌─────────────────┐
│   RESOURCES      │    N:M  │  RESOURCE_TAGS  │
│──────────────────│◄────────┤─────────────────│
│ PK id            │         │ PK resource_id  │
│ FK provider_id   │         │ PK tag_id       │
│    name          │         └─────────────────┘
│    type          │                 │
│    specs (JSONB) │                 │
│    price_per_hour│                 │
│    status        │         ┌───────▼─────┐
└───────┬──────────┘         │    TAGS     │
        │                    │─────────────│
        │ 1:N                │ PK id       │
        │                    │    name     │
        │                    └─────────────┘
        │
┌───────▼──────────┐
│    BOOKINGS      │
│──────────────────│
│ PK id            │
│ FK user_id       │
│ FK resource_id   │
│    start_time    │
│    end_time      │
│    total_cost    │
│    status        │
└───────┬──────────┘
        │
        │ 1:1
        │
┌───────▼──────────┐
│    PAYMENTS      │
│──────────────────│
│ PK id            │
│ FK booking_id    │
│    amount        │
│    method        │
│    status        │
│    tx_hash       │
└───────┬──────────┘
        │
        │ 1:N
        │
┌───────▼──────────┐
│     REVIEWS      │
│──────────────────│
│ PK id            │
│ FK booking_id    │
│ FK reviewer_id   │
│ FK reviewee_id   │
│    rating        │
│    comment       │
└──────────────────┘

┌──────────────────┐
│    MESSAGES      │
│──────────────────│
│ PK id            │
│ FK conversation_id
│ FK sender_id     │
│    content       │
│    sent_at       │
└──────────────────┘
        ▲
        │
        │ N:1
        │
┌───────┴──────────┐
│  CONVERSATIONS   │
│──────────────────│
│ PK id            │
│ FK user1_id      │
│ FK user2_id      │
│    created_at    │
└──────────────────┘

┌──────────────────┐
│  NOTIFICATIONS   │
│──────────────────│
│ PK id            │
│ FK user_id       │
│    type          │
│    content       │
│    is_read       │
│    created_at    │
└──────────────────┘

┌──────────────────┐
│ ACTIVITY_LOGS    │
│──────────────────│
│ PK id            │
│ FK user_id       │
│    action        │
│    entity_type   │
│    entity_id     │
│    metadata      │
│    timestamp     │
└──────────────────┘
```

### Detailed Relationships

```
Users (1) ────< (N) Resources
  │
  ├──< (N) Bookings
  │
  ├──< (N) Reviews (as reviewer)
  │
  ├──< (N) Reviews (as reviewee)
  │
  ├──< (N) Messages
  │
  └──< (N) Notifications

Resources (1) ────< (N) Bookings
  │
  └──< (N) Resource_Tags

Bookings (1) ────= (1) Payments
  │
  └──< (N) Reviews

Tags (1) ────< (N) Resource_Tags
```

---

## Core Tables

### 1. Users Table

```sql
CREATE TABLE users (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Authentication
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(255),

    -- Profile information
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    display_name VARCHAR(200),
    avatar_url TEXT,
    bio TEXT,
    phone VARCHAR(20),

    -- Role and permissions
    role VARCHAR(20) NOT NULL CHECK (role IN ('buyer', 'provider', 'admin')),

    -- Provider-specific fields
    company_name VARCHAR(255),
    company_website TEXT,
    provider_status VARCHAR(20) CHECK (provider_status IN ('pending', 'approved', 'suspended')),

    -- Account status
    is_active BOOLEAN DEFAULT TRUE,
    is_banned BOOLEAN DEFAULT FALSE,
    ban_reason TEXT,

    -- Reputation
    rating_avg DECIMAL(3, 2) DEFAULT 0.00 CHECK (rating_avg >= 0 AND rating_avg <= 5),
    rating_count INTEGER DEFAULT 0,
    total_bookings INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP, -- Soft delete
    last_login_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_created_at ON users(created_at DESC);
CREATE INDEX idx_users_rating ON users(rating_avg DESC);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = TRUE;

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE users IS 'User accounts (buyers, providers, admins)';
COMMENT ON COLUMN users.rating_avg IS 'Average rating from 0.00 to 5.00';
```

### 2. Resources Table

```sql
CREATE TABLE resources (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Provider reference
    provider_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Basic information
    name VARCHAR(255) NOT NULL,
    description TEXT,
    resource_type VARCHAR(50) NOT NULL CHECK (resource_type IN ('cpu', 'gpu', 'storage', 'bandwidth', 'full_machine')),

    -- Specifications (flexible JSON for different resource types)
    specs JSONB NOT NULL,
    /*
    Example specs:
    {
      "cpu": {"cores": 16, "model": "AMD EPYC 7763", "frequency_ghz": 3.5},
      "ram": {"size_gb": 64, "type": "DDR4"},
      "gpu": [
        {"model": "NVIDIA RTX 4090", "vram_gb": 24, "count": 2}
      ],
      "storage": {"type": "NVMe", "size_tb": 2},
      "network": {"bandwidth_gbps": 10},
      "os": ["Ubuntu 22.04", "Windows Server 2022"],
      "location": {"region": "us-east-1", "datacenter": "AWS"}
    }
    */

    -- Pricing
    price_per_hour DECIMAL(10, 4) NOT NULL CHECK (price_per_hour >= 0),
    currency VARCHAR(3) DEFAULT 'USD',
    billing_increment_minutes INTEGER DEFAULT 60, -- Minimum billing increment

    -- Availability
    availability_status VARCHAR(20) NOT NULL DEFAULT 'available'
        CHECK (availability_status IN ('available', 'in_use', 'maintenance', 'offline')),
    total_hours_available INTEGER DEFAULT 0,
    total_hours_booked INTEGER DEFAULT 0,

    -- Location
    location_region VARCHAR(100),
    location_country VARCHAR(2), -- ISO country code
    location_city VARCHAR(100),
    location_lat DECIMAL(10, 8),
    location_lng DECIMAL(11, 8),

    -- Performance metrics
    uptime_percentage DECIMAL(5, 2) DEFAULT 100.00,
    avg_response_time_ms INTEGER,

    -- Reputation
    rating_avg DECIMAL(3, 2) DEFAULT 0.00 CHECK (rating_avg >= 0 AND rating_avg <= 5),
    rating_count INTEGER DEFAULT 0,
    total_bookings INTEGER DEFAULT 0,
    total_revenue DECIMAL(12, 2) DEFAULT 0,

    -- Search optimization
    search_vector tsvector,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP,
    last_booked_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_resources_provider ON resources(provider_id);
CREATE INDEX idx_resources_type ON resources(resource_type);
CREATE INDEX idx_resources_status ON resources(availability_status);
CREATE INDEX idx_resources_price ON resources(price_per_hour);
CREATE INDEX idx_resources_rating ON resources(rating_avg DESC);
CREATE INDEX idx_resources_location ON resources(location_region, location_country);
CREATE INDEX idx_resources_created_at ON resources(created_at DESC);

-- JSON indexes (for querying specs)
CREATE INDEX idx_resources_specs_gpu ON resources USING GIN ((specs->'gpu'));
CREATE INDEX idx_resources_specs_cpu_cores ON resources ((specs->'cpu'->>'cores'));
CREATE INDEX idx_resources_specs_ram ON resources ((specs->'ram'->>'size_gb'));

-- Full-text search index
CREATE INDEX idx_resources_search ON resources USING GIN(search_vector);

-- Geospatial index (if using PostGIS)
-- CREATE INDEX idx_resources_location_point ON resources USING GIST (ll_to_earth(location_lat, location_lng));

-- Update timestamp trigger
CREATE TRIGGER update_resources_updated_at BEFORE UPDATE ON resources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Auto-update search vector
CREATE OR REPLACE FUNCTION update_resource_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('english',
        COALESCE(NEW.name, '') || ' ' ||
        COALESCE(NEW.description, '') || ' ' ||
        COALESCE(NEW.resource_type, '') || ' ' ||
        COALESCE(NEW.specs::text, '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_resources_search_vector BEFORE INSERT OR UPDATE ON resources
    FOR EACH ROW EXECUTE FUNCTION update_resource_search_vector();

COMMENT ON TABLE resources IS 'Compute resources available for rent';
COMMENT ON COLUMN resources.specs IS 'JSONB specifications (CPU, RAM, GPU, etc.)';
```

### 3. Bookings Table (Partitioned)

```sql
CREATE TABLE bookings (
    -- Primary key
    id UUID DEFAULT gen_random_uuid(),

    -- References
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resource_id UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,

    -- Booking details
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    duration_hours DECIMAL(10, 2) GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (end_time - start_time)) / 3600
    ) STORED,

    -- Pricing
    price_per_hour DECIMAL(10, 4) NOT NULL, -- Snapshot at booking time
    total_cost DECIMAL(12, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending',      -- Awaiting payment
        'confirmed',    -- Paid, awaiting start
        'active',       -- Currently running
        'completed',    -- Finished successfully
        'cancelled',    -- Cancelled before start
        'failed',       -- Failed during execution
        'disputed'      -- Under dispute
    )),

    -- Cancellation
    cancelled_by UUID REFERENCES users(id),
    cancelled_at TIMESTAMP,
    cancellation_reason TEXT,
    refund_amount DECIMAL(12, 2),

    -- Extension/modification
    original_end_time TIMESTAMP,
    extension_count INTEGER DEFAULT 0,

    -- Blockchain reference (if using hybrid architecture)
    escrow_id VARCHAR(255),
    blockchain_tx_hash VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CHECK (end_time > start_time),
    CHECK (total_cost >= 0),
    CHECK (refund_amount >= 0)
) PARTITION BY RANGE (start_time);

-- Create partitions (monthly)
CREATE TABLE bookings_2025_01 PARTITION OF bookings
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE bookings_2025_02 PARTITION OF bookings
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

CREATE TABLE bookings_2025_03 PARTITION OF bookings
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

-- Add more partitions as needed...

-- Indexes on parent table (applied to all partitions)
CREATE INDEX idx_bookings_user ON bookings(user_id, start_time DESC);
CREATE INDEX idx_bookings_resource ON bookings(resource_id, start_time DESC);
CREATE INDEX idx_bookings_status ON bookings(status);
CREATE INDEX idx_bookings_start_time ON bookings(start_time DESC);
CREATE INDEX idx_bookings_created_at ON bookings(created_at DESC);

-- Trigger for update timestamp
CREATE TRIGGER update_bookings_updated_at BEFORE UPDATE ON bookings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE bookings IS 'Resource bookings (partitioned by start_time)';
```

### 4. Payments Table

```sql
CREATE TABLE payments (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Booking reference
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,

    -- Payer and payee
    payer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    payee_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Payment details
    amount DECIMAL(12, 2) NOT NULL CHECK (amount >= 0),
    currency VARCHAR(3) DEFAULT 'USD',
    payment_method VARCHAR(50) NOT NULL CHECK (payment_method IN (
        'credit_card',
        'debit_card',
        'paypal',
        'stripe',
        'crypto_eth',
        'crypto_btc',
        'crypto_usdc',
        'bank_transfer',
        'wallet_balance'
    )),

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending',
        'processing',
        'completed',
        'failed',
        'refunded',
        'partially_refunded'
    )),

    -- External references
    external_payment_id VARCHAR(255), -- Stripe, PayPal, etc.
    blockchain_tx_hash VARCHAR(255),
    blockchain_network VARCHAR(50),
    blockchain_confirmations INTEGER,

    -- Refund
    refund_amount DECIMAL(12, 2) DEFAULT 0 CHECK (refund_amount >= 0),
    refund_reason TEXT,
    refunded_at TIMESTAMP,

    -- Platform fee
    platform_fee_percentage DECIMAL(5, 2) DEFAULT 10.00,
    platform_fee_amount DECIMAL(12, 2) GENERATED ALWAYS AS (
        amount * platform_fee_percentage / 100
    ) STORED,
    net_amount DECIMAL(12, 2) GENERATED ALWAYS AS (
        amount - (amount * platform_fee_percentage / 100)
    ) STORED,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,

    -- Metadata
    metadata JSONB
);

-- Indexes
CREATE INDEX idx_payments_booking ON payments(booking_id);
CREATE INDEX idx_payments_payer ON payments(payer_id, created_at DESC);
CREATE INDEX idx_payments_payee ON payments(payee_id, created_at DESC);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_method ON payments(payment_method);
CREATE INDEX idx_payments_created_at ON payments(created_at DESC);
CREATE INDEX idx_payments_external_id ON payments(external_payment_id) WHERE external_payment_id IS NOT NULL;

CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON payments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE payments IS 'Payment transactions for bookings';
```

### 5. Reviews Table

```sql
CREATE TABLE reviews (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- References
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    reviewer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reviewee_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resource_id UUID REFERENCES resources(id) ON DELETE SET NULL,

    -- Review content
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,

    -- Detailed ratings (optional)
    rating_accuracy INTEGER CHECK (rating_accuracy >= 1 AND rating_accuracy <= 5),
    rating_performance INTEGER CHECK (rating_performance >= 1 AND rating_performance <= 5),
    rating_communication INTEGER CHECK (rating_communication >= 1 AND rating_communication <= 5),
    rating_value INTEGER CHECK (rating_value >= 1 AND rating_value <= 5),

    -- Response
    response TEXT,
    response_at TIMESTAMP,

    -- Flags
    is_verified BOOLEAN DEFAULT FALSE, -- Verified booking completion
    is_flagged BOOLEAN DEFAULT FALSE,
    flag_reason TEXT,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    UNIQUE (booking_id, reviewer_id) -- One review per booking per reviewer
);

-- Indexes
CREATE INDEX idx_reviews_booking ON reviews(booking_id);
CREATE INDEX idx_reviews_reviewer ON reviews(reviewer_id, created_at DESC);
CREATE INDEX idx_reviews_reviewee ON reviews(reviewee_id, created_at DESC);
CREATE INDEX idx_reviews_resource ON reviews(resource_id, created_at DESC);
CREATE INDEX idx_reviews_rating ON reviews(rating);
CREATE INDEX idx_reviews_created_at ON reviews(created_at DESC);

CREATE TRIGGER update_reviews_updated_at BEFORE UPDATE ON reviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE reviews IS 'User and resource reviews';
```

### 6. Tags Table

```sql
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    category VARCHAR(50), -- e.g., 'hardware', 'software', 'use_case'
    description TEXT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tags_name ON tags(name);
CREATE INDEX idx_tags_category ON tags(category);

COMMENT ON TABLE tags IS 'Tags for categorizing resources';
```

### 7. Resource Tags Junction Table

```sql
CREATE TABLE resource_tags (
    resource_id UUID NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (resource_id, tag_id)
);

CREATE INDEX idx_resource_tags_resource ON resource_tags(resource_id);
CREATE INDEX idx_resource_tags_tag ON resource_tags(tag_id);

COMMENT ON TABLE resource_tags IS 'Many-to-many relationship between resources and tags';
```

### 8. Messages Table (Partitioned)

```sql
CREATE TABLE messages (
    id UUID DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipient_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    content TEXT NOT NULL,
    content_type VARCHAR(20) DEFAULT 'text' CHECK (content_type IN ('text', 'image', 'file', 'link')),

    -- Attachments
    attachments JSONB, -- Array of file URLs

    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,

    -- Timestamps
    sent_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (sent_at);

-- Create partitions (monthly)
CREATE TABLE messages_2025_01 PARTITION OF messages
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE messages_2025_02 PARTITION OF messages
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- Indexes
CREATE INDEX idx_messages_conversation ON messages(conversation_id, sent_at DESC);
CREATE INDEX idx_messages_sender ON messages(sender_id, sent_at DESC);
CREATE INDEX idx_messages_recipient ON messages(recipient_id, is_read, sent_at DESC);

COMMENT ON TABLE messages IS 'Chat messages between users (partitioned by sent_at)';
```

### 9. Conversations Table

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user1_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user2_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    last_message_at TIMESTAMP,
    last_message_preview TEXT,

    -- Unread counts
    unread_count_user1 INTEGER DEFAULT 0,
    unread_count_user2 INTEGER DEFAULT 0,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Ensure unique conversation between two users
    UNIQUE (user1_id, user2_id),
    CHECK (user1_id < user2_id) -- Enforce ordering to prevent duplicates
);

CREATE INDEX idx_conversations_user1 ON conversations(user1_id, last_message_at DESC);
CREATE INDEX idx_conversations_user2 ON conversations(user2_id, last_message_at DESC);

COMMENT ON TABLE conversations IS 'Conversations between two users';
```

### 10. Notifications Table (Partitioned)

```sql
CREATE TABLE notifications (
    id UUID DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    type VARCHAR(50) NOT NULL CHECK (type IN (
        'booking_confirmed',
        'booking_started',
        'booking_completed',
        'booking_cancelled',
        'payment_received',
        'payment_failed',
        'new_message',
        'new_review',
        'resource_available',
        'system_alert'
    )),

    title VARCHAR(255) NOT NULL,
    content TEXT,
    link TEXT, -- Deep link to relevant page

    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,

    -- Delivery channels
    sent_email BOOLEAN DEFAULT FALSE,
    sent_push BOOLEAN DEFAULT FALSE,
    sent_sms BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Create partitions (monthly)
CREATE TABLE notifications_2025_01 PARTITION OF notifications
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE notifications_2025_02 PARTITION OF notifications
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- Indexes
CREATE INDEX idx_notifications_user ON notifications(user_id, is_read, created_at DESC);
CREATE INDEX idx_notifications_type ON notifications(type);

COMMENT ON TABLE notifications IS 'User notifications (partitioned by created_at)';
```

### 11. Activity Logs Table (Partitioned)

```sql
CREATE TABLE activity_logs (
    id UUID DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,

    -- Context
    ip_address INET,
    user_agent TEXT,
    metadata JSONB,

    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (timestamp);

-- Create partitions (monthly)
CREATE TABLE activity_logs_2025_01 PARTITION OF activity_logs
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE activity_logs_2025_02 PARTITION OF activity_logs
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- Indexes
CREATE INDEX idx_activity_logs_user ON activity_logs(user_id, timestamp DESC);
CREATE INDEX idx_activity_logs_action ON activity_logs(action, timestamp DESC);
CREATE INDEX idx_activity_logs_entity ON activity_logs(entity_type, entity_id);

COMMENT ON TABLE activity_logs IS 'User activity logs for analytics (partitioned by timestamp)';
```

---

## Indexing Strategy

### Index Types in PostgreSQL

#### 1. B-Tree Index (Default)
**Best for**: Equality and range queries, sorting

```sql
-- Equality
CREATE INDEX idx_users_email ON users(email);

-- Range queries
CREATE INDEX idx_bookings_start_time ON bookings(start_time DESC);

-- Composite index (multi-column)
CREATE INDEX idx_resources_type_price ON resources(resource_type, price_per_hour);
```

#### 2. GIN Index (Generalized Inverted Index)
**Best for**: JSONB, full-text search, arrays

```sql
-- JSONB queries
CREATE INDEX idx_resources_specs ON resources USING GIN(specs);

-- Full-text search
CREATE INDEX idx_resources_search ON resources USING GIN(search_vector);

-- Array queries
CREATE INDEX idx_resource_os ON resources USING GIN((specs->'os'));
```

#### 3. GiST Index (Generalized Search Tree)
**Best for**: Geospatial queries, range types

```sql
-- Geospatial (requires PostGIS)
CREATE EXTENSION IF NOT EXISTS postgis;
ALTER TABLE resources ADD COLUMN location GEOGRAPHY(POINT, 4326);
CREATE INDEX idx_resources_location ON resources USING GIST(location);
```

#### 4. Hash Index
**Best for**: Equality only (rarely used, B-tree is usually better)

```sql
CREATE INDEX idx_users_email_hash ON users USING HASH(email);
```

#### 5. Partial Index
**Best for**: Filtering on subset of data

```sql
-- Index only active users
CREATE INDEX idx_users_active ON users(email) WHERE is_active = TRUE;

-- Index only available resources
CREATE INDEX idx_resources_available ON resources(price_per_hour)
    WHERE availability_status = 'available';
```

#### 6. Expression Index
**Best for**: Computed values, case-insensitive queries

```sql
-- Case-insensitive search
CREATE INDEX idx_users_email_lower ON users(LOWER(email));

-- Extract JSON values
CREATE INDEX idx_resources_gpu_model ON resources((specs->'gpu'->0->>'model'));
```

### Indexing Guidelines

```
✓ Index foreign keys (JOIN performance)
✓ Index WHERE clause columns
✓ Index ORDER BY columns
✓ Use partial indexes for filtered queries
✓ Use composite indexes for multi-column queries
✓ Monitor index usage (pg_stat_user_indexes)

✗ Don't over-index (slows INSERTs/UPDATEs)
✗ Don't index very small tables (<1000 rows)
✗ Don't index high-cardinality columns without need
```

### Index Maintenance

```sql
-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan ASC;

-- Find unused indexes
SELECT
    schemaname,
    tablename,
    indexname
FROM pg_stat_user_indexes
WHERE idx_scan = 0
    AND schemaname = 'public';

-- Reindex (rebuild indexes)
REINDEX TABLE resources;
REINDEX INDEX idx_resources_price;
```

---

## Partitioning for Scale

### When to Partition

```
✓ Tables with >10M rows
✓ Time-series data (logs, events, bookings)
✓ Archiving old data
✓ Query patterns that filter on partition key
```

### Partition Strategies

#### 1. Range Partitioning (Most Common)

**Example: Bookings by month**

```sql
CREATE TABLE bookings (...) PARTITION BY RANGE (start_time);

-- Create partitions
CREATE TABLE bookings_2025_01 PARTITION OF bookings
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- Automated partition creation function
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name TEXT, start_date DATE)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    start_timestamp TIMESTAMP;
    end_timestamp TIMESTAMP;
BEGIN
    partition_name := table_name || '_' || TO_CHAR(start_date, 'YYYY_MM');
    start_timestamp := start_date;
    end_timestamp := start_date + INTERVAL '1 month';

    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
        partition_name, table_name, start_timestamp, end_timestamp
    );
END;
$$ LANGUAGE plpgsql;

-- Create partitions for next 12 months
DO $$
BEGIN
    FOR i IN 0..11 LOOP
        PERFORM create_monthly_partition('bookings', DATE '2025-01-01' + (i || ' months')::INTERVAL);
    END LOOP;
END $$;
```

#### 2. List Partitioning

**Example: Users by region**

```sql
CREATE TABLE users_partitioned (...) PARTITION BY LIST (location_region);

CREATE TABLE users_us PARTITION OF users_partitioned
    FOR VALUES IN ('us-east-1', 'us-west-1', 'us-west-2');

CREATE TABLE users_eu PARTITION OF users_partitioned
    FOR VALUES IN ('eu-west-1', 'eu-central-1');

CREATE TABLE users_ap PARTITION OF users_partitioned
    FOR VALUES IN ('ap-southeast-1', 'ap-northeast-1');
```

#### 3. Hash Partitioning

**Example: Distribute data evenly**

```sql
CREATE TABLE activity_logs_hash (...) PARTITION BY HASH (user_id);

CREATE TABLE activity_logs_p0 PARTITION OF activity_logs_hash
    FOR VALUES WITH (MODULUS 4, REMAINDER 0);

CREATE TABLE activity_logs_p1 PARTITION OF activity_logs_hash
    FOR VALUES WITH (MODULUS 4, REMAINDER 1);

CREATE TABLE activity_logs_p2 PARTITION OF activity_logs_hash
    FOR VALUES WITH (MODULUS 4, REMAINDER 2);

CREATE TABLE activity_logs_p3 PARTITION OF activity_logs_hash
    FOR VALUES WITH (MODULUS 4, REMAINDER 3);
```

### Partition Maintenance

```sql
-- Detach old partition (for archiving)
ALTER TABLE bookings DETACH PARTITION bookings_2024_01;

-- Archive to separate tablespace or database
-- Then drop
DROP TABLE bookings_2024_01;

-- Attach partition (restore archived data)
CREATE TABLE bookings_2024_01 (LIKE bookings INCLUDING ALL);
ALTER TABLE bookings ATTACH PARTITION bookings_2024_01
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

---

## Database Constraints

### 1. Primary Keys

```sql
-- UUID primary keys (recommended for distributed systems)
id UUID PRIMARY KEY DEFAULT gen_random_uuid()

-- Auto-incrementing (traditional)
id SERIAL PRIMARY KEY
```

### 2. Foreign Keys

```sql
-- Cascade delete (delete child records when parent is deleted)
provider_id UUID REFERENCES users(id) ON DELETE CASCADE

-- Set null (keep child records, nullify reference)
resource_id UUID REFERENCES resources(id) ON DELETE SET NULL

-- Restrict (prevent deletion if child records exist)
user_id UUID REFERENCES users(id) ON DELETE RESTRICT
```

### 3. Check Constraints

```sql
-- Value range
rating INTEGER CHECK (rating >= 1 AND rating <= 5)

-- Enum-like values
status VARCHAR(20) CHECK (status IN ('pending', 'completed', 'failed'))

-- Date logic
CHECK (end_time > start_time)

-- Positive values
CHECK (price_per_hour >= 0)
```

### 4. Unique Constraints

```sql
-- Single column
email VARCHAR(255) UNIQUE

-- Multiple columns (composite unique)
UNIQUE (user1_id, user2_id)
```

### 5. Not Null Constraints

```sql
email VARCHAR(255) NOT NULL
```

---

## Example Queries

### 1. User Management

**Register new user:**
```sql
INSERT INTO users (email, password_hash, first_name, last_name, role)
VALUES (
    'john@example.com',
    '$2b$10$...',  -- bcrypt hash
    'John',
    'Doe',
    'buyer'
)
RETURNING id, email, first_name, last_name, role, created_at;
```

**Find user by email:**
```sql
SELECT id, email, first_name, last_name, role, is_active
FROM users
WHERE email = 'john@example.com'
    AND deleted_at IS NULL;
```

**Update user profile:**
```sql
UPDATE users
SET
    first_name = 'John',
    last_name = 'Smith',
    updated_at = NOW()
WHERE id = 'user-uuid'
RETURNING *;
```

### 2. Resource Search & Filtering

**Basic search:**
```sql
SELECT
    r.id,
    r.name,
    r.description,
    r.resource_type,
    r.specs,
    r.price_per_hour,
    r.availability_status,
    r.rating_avg,
    u.display_name AS provider_name
FROM resources r
JOIN users u ON r.provider_id = u.id
WHERE r.availability_status = 'available'
    AND r.deleted_at IS NULL
ORDER BY r.rating_avg DESC, r.price_per_hour ASC
LIMIT 20 OFFSET 0;
```

**Advanced filtering (GPU resources with specs):**
```sql
SELECT
    r.id,
    r.name,
    r.specs->'gpu' AS gpu_specs,
    r.specs->'cpu' AS cpu_specs,
    r.specs->'ram' AS ram_specs,
    r.price_per_hour,
    r.rating_avg
FROM resources r
WHERE r.resource_type = 'gpu'
    AND r.availability_status = 'available'
    AND r.specs->'gpu'->0->>'model' ILIKE '%RTX 4090%'
    AND (r.specs->'ram'->>'size_gb')::INTEGER >= 32
    AND r.price_per_hour BETWEEN 1.0 AND 10.0
ORDER BY r.rating_avg DESC
LIMIT 20;
```

**Full-text search:**
```sql
SELECT
    r.id,
    r.name,
    r.description,
    r.price_per_hour,
    ts_rank(r.search_vector, query) AS rank
FROM resources r,
    to_tsquery('english', 'GPU & machine & learning') AS query
WHERE r.search_vector @@ query
    AND r.availability_status = 'available'
ORDER BY rank DESC, r.rating_avg DESC
LIMIT 20;
```

**Geospatial search (nearby resources):**
```sql
-- Using PostGIS
SELECT
    r.id,
    r.name,
    r.location_city,
    ST_Distance(
        r.location,
        ST_MakePoint(-73.9857, 40.7484)::geography -- User's location (NYC)
    ) / 1000 AS distance_km
FROM resources r
WHERE r.availability_status = 'available'
    AND ST_DWithin(
        r.location,
        ST_MakePoint(-73.9857, 40.7484)::geography,
        100000  -- 100km radius
    )
ORDER BY distance_km ASC
LIMIT 20;
```

### 3. Booking Management

**Create booking:**
```sql
INSERT INTO bookings (
    user_id,
    resource_id,
    start_time,
    end_time,
    price_per_hour,
    total_cost,
    status
)
VALUES (
    'user-uuid',
    'resource-uuid',
    '2025-02-01 10:00:00',
    '2025-02-01 14:00:00',
    5.00,
    20.00,  -- 4 hours * $5/hour
    'pending'
)
RETURNING *;
```

**Check resource availability:**
```sql
SELECT
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM bookings
            WHERE resource_id = 'resource-uuid'
                AND status IN ('confirmed', 'active')
                AND (
                    (start_time, end_time) OVERLAPS
                    (TIMESTAMP '2025-02-01 10:00:00', TIMESTAMP '2025-02-01 14:00:00')
                )
        ) THEN FALSE
        ELSE TRUE
    END AS is_available;
```

**Find user's active bookings:**
```sql
SELECT
    b.id,
    b.start_time,
    b.end_time,
    b.total_cost,
    b.status,
    r.name AS resource_name,
    r.specs,
    u.display_name AS provider_name
FROM bookings b
JOIN resources r ON b.resource_id = r.id
JOIN users u ON r.provider_id = u.id
WHERE b.user_id = 'user-uuid'
    AND b.status IN ('confirmed', 'active')
ORDER BY b.start_time ASC;
```

### 4. Analytics Queries

**Provider revenue summary:**
```sql
SELECT
    u.id,
    u.display_name,
    COUNT(b.id) AS total_bookings,
    SUM(b.total_cost) AS total_revenue,
    AVG(b.total_cost) AS avg_booking_value,
    SUM(b.duration_hours) AS total_hours_booked
FROM users u
JOIN resources r ON u.id = r.provider_id
JOIN bookings b ON r.id = b.resource_id
WHERE b.status = 'completed'
    AND b.start_time >= '2025-01-01'
GROUP BY u.id, u.display_name
ORDER BY total_revenue DESC;
```

**Most popular resources:**
```sql
SELECT
    r.id,
    r.name,
    r.resource_type,
    r.price_per_hour,
    COUNT(b.id) AS booking_count,
    SUM(b.total_cost) AS total_revenue,
    AVG(b.total_cost) AS avg_booking_value,
    r.rating_avg
FROM resources r
LEFT JOIN bookings b ON r.id = b.resource_id AND b.status = 'completed'
WHERE r.deleted_at IS NULL
GROUP BY r.id
ORDER BY booking_count DESC
LIMIT 50;
```

**Platform metrics (daily):**
```sql
SELECT
    DATE(b.created_at) AS date,
    COUNT(*) AS total_bookings,
    COUNT(*) FILTER (WHERE b.status = 'completed') AS completed_bookings,
    COUNT(*) FILTER (WHERE b.status = 'cancelled') AS cancelled_bookings,
    SUM(b.total_cost) AS total_gmv,
    SUM(b.total_cost) FILTER (WHERE b.status = 'completed') AS actual_revenue,
    COUNT(DISTINCT b.user_id) AS unique_users,
    COUNT(DISTINCT b.resource_id) AS unique_resources
FROM bookings b
WHERE b.created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(b.created_at)
ORDER BY date DESC;
```

### 5. Materialized Views (for complex analytics)

```sql
-- Create materialized view for dashboard metrics
CREATE MATERIALIZED VIEW daily_metrics AS
SELECT
    DATE(created_at) AS date,
    COUNT(*) AS new_users,
    COUNT(*) FILTER (WHERE role = 'provider') AS new_providers,
    COUNT(*) FILTER (WHERE role = 'buyer') AS new_buyers
FROM users
GROUP BY DATE(created_at);

CREATE INDEX idx_daily_metrics_date ON daily_metrics(date DESC);

-- Refresh periodically (e.g., daily via cron)
REFRESH MATERIALIZED VIEW CONCURRENTLY daily_metrics;
```

---

## Migration Strategy

### Migration Tools

**Recommended**: TypeORM, Prisma, or Knex.js for Node.js

**Example with TypeORM:**

```typescript
// migrations/1704067200000-CreateUsersTable.ts
import { MigrationInterface, QueryRunner, Table } from "typeorm";

export class CreateUsersTable1704067200000 implements MigrationInterface {
    public async up(queryRunner: QueryRunner): Promise<void> {
        await queryRunner.createTable(new Table({
            name: "users",
            columns: [
                {
                    name: "id",
                    type: "uuid",
                    isPrimary: true,
                    default: "gen_random_uuid()"
                },
                {
                    name: "email",
                    type: "varchar",
                    length: "255",
                    isUnique: true,
                    isNullable: false
                },
                // ... more columns
            ]
        }), true);

        // Create indexes
        await queryRunner.createIndex("users", {
            name: "idx_users_email",
            columnNames: ["email"]
        });
    }

    public async down(queryRunner: QueryRunner): Promise<void> {
        await queryRunner.dropTable("users");
    }
}
```

### Migration Best Practices

```
✓ Use migrations for all schema changes
✓ Test migrations on staging first
✓ Backup database before production migrations
✓ Use transactions for atomic changes
✓ Write reversible migrations (up/down)
✓ Version control all migrations
✓ Run migrations during maintenance window for large changes
```

---

## Performance Optimization

### 1. Query Optimization

```sql
-- Use EXPLAIN ANALYZE to understand query performance
EXPLAIN ANALYZE
SELECT *
FROM resources
WHERE resource_type = 'gpu'
    AND price_per_hour < 10;

-- Results show:
-- - Sequential Scan vs Index Scan
-- - Estimated cost vs actual cost
-- - Rows returned
-- - Execution time
```

### 2. Connection Pooling

```javascript
// Node.js with pg
const { Pool } = require('pg');

const pool = new Pool({
    max: 20,  // Maximum connections
    min: 5,   // Minimum connections
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 2000,
});
```

### 3. Prepared Statements

```sql
-- Prepare statement (reduces parsing overhead)
PREPARE get_resource (UUID) AS
    SELECT * FROM resources WHERE id = $1;

-- Execute
EXECUTE get_resource('resource-uuid');
```

### 4. Vacuuming (PostgreSQL maintenance)

```sql
-- Analyze tables (update statistics for query planner)
ANALYZE users;

-- Vacuum (reclaim storage, update stats)
VACUUM ANALYZE resources;

-- Auto-vacuum (configure in postgresql.conf)
-- Already enabled by default in PostgreSQL 10+
```

### 5. Monitor Slow Queries

```sql
-- Enable slow query logging
-- In postgresql.conf:
-- log_min_duration_statement = 1000  # Log queries taking > 1 second

-- View slow queries
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 20;
```

---

## Conclusion

This database schema provides a solid foundation for a scalable compute marketplace platform with:

- Normalized structure for data integrity
- JSONB for flexible specifications
- Partitioning for scalability (100M+ rows)
- Comprehensive indexing strategy
- Full-text and geospatial search capabilities
- Audit trails and soft deletes
- Performance optimization patterns

**Key Takeaways:**
1. Use UUIDs for distributed systems
2. Partition large tables (bookings, messages, logs)
3. Index strategically (WHERE, JOIN, ORDER BY columns)
4. Leverage JSONB for flexible data
5. Implement soft deletes for data integrity
6. Use materialized views for complex analytics
7. Monitor and optimize continuously

---

**Document Version**: 1.0
**Last Updated**: 2025-10-14
**Author**: Database Architecture Team
