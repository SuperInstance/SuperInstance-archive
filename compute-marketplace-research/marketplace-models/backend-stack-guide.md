# Backend Stack Guide: Technology Selection & Architecture

## Executive Summary

This document provides comprehensive guidance on backend technology selection for a compute marketplace platform. It covers language/framework choices, database selection, caching strategies, message queues, and provides detailed recommendations with code examples and project structure.

**Quick Recommendation**: **Node.js (TypeScript) + Express/NestJS + PostgreSQL + Redis + RabbitMQ** for optimal balance of performance, developer productivity, and ecosystem maturity.

---

## Table of Contents

1. [Language & Framework Selection](#language--framework-selection)
2. [Database Selection](#database-selection)
3. [Caching Strategy](#caching-strategy)
4. [Message Queues & Background Jobs](#message-queues--background-jobs)
5. [Recommended Stack](#recommended-stack)
6. [Project Structure](#project-structure)
7. [Code Examples](#code-examples)
8. [Deployment Considerations](#deployment-considerations)

---

## Language & Framework Selection

### Comparison Matrix (2025)

| Language | Performance | Dev Speed | Ecosystem | Scalability | Team Availability | Best For |
|----------|-------------|-----------|-----------|-------------|-------------------|----------|
| **Node.js** | Good | Excellent | Excellent | Excellent | High | APIs, real-time, microservices |
| **Python** | Fair | Excellent | Excellent | Good | High | AI/ML, data processing, rapid prototyping |
| **Go** | Excellent | Good | Good | Excellent | Medium | Microservices, DevOps tools, high-throughput |
| **Rust** | Excellent | Fair | Growing | Excellent | Low | High-performance, systems, memory-critical |

### Detailed Analysis

#### 1. Node.js (TypeScript)

**Performance Metrics (2025):**
- Request handling: ~10,000 req/sec per core
- JSON parsing: Good (native V8 optimization)
- I/O operations: Excellent (async/await, event loop)
- CPU-heavy tasks: Fair (single-threaded, use worker threads)

**Advantages:**
```
✓ Excellent for I/O-bound operations (APIs, databases)
✓ Massive ecosystem (npm: 2M+ packages)
✓ Large talent pool (~30% of backend developers)
✓ TypeScript adds type safety
✓ Great for microservices (lightweight)
✓ Real-time capabilities (WebSockets, Socket.io)
✓ JavaScript/TypeScript across stack (frontend + backend)
✓ Mature frameworks (Express, NestJS, Fastify)
✓ Excellent async/await support
```

**Disadvantages:**
```
✗ Single-threaded (CPU-bound tasks are blocking)
✗ Callback hell (mitigated by async/await)
✗ Less strict typing than compiled languages (mitigated by TypeScript)
✗ Slower than Go/Rust for CPU-intensive tasks
```

**Best Use Cases:**
- RESTful APIs
- Real-time applications (chat, notifications)
- Microservices
- GraphQL servers
- Serverless functions

**Salary Range (2025):**
- Junior: $70K-100K
- Mid: $100K-140K
- Senior: $140K-180K

**Framework Recommendations:**

1. **Express.js** (Minimalist, most popular)
```javascript
// Pros: Simple, flexible, huge ecosystem, lightweight
// Cons: No built-in structure, need to add middleware manually

const express = require('express');
const app = express();

app.get('/api/resources', async (req, res) => {
  const resources = await Resource.find(req.query);
  res.json(resources);
});

app.listen(3000);
```

2. **NestJS** (Enterprise, opinionated)
```typescript
// Pros: TypeScript-first, Angular-like structure, dependency injection, built-in testing
// Cons: Steeper learning curve, more boilerplate

@Controller('resources')
export class ResourceController {
  constructor(private readonly resourceService: ResourceService) {}

  @Get()
  async findAll(@Query() query: ResourceQueryDto): Promise<Resource[]> {
    return this.resourceService.findAll(query);
  }
}
```

3. **Fastify** (High-performance alternative)
```javascript
// Pros: 2x faster than Express, schema-based validation, TypeScript support
// Cons: Smaller ecosystem than Express

const fastify = require('fastify')({ logger: true });

fastify.get('/api/resources', async (request, reply) => {
  const resources = await Resource.find(request.query);
  return resources;
});

fastify.listen(3000);
```

**Recommendation:** **NestJS for enterprise applications** (better structure, testing, scalability), **Express for simpler APIs** (faster setup, more flexible).

---

#### 2. Python (Django/FastAPI)

**Performance Metrics (2025):**
- Request handling: ~2,000-5,000 req/sec per core
- JSON parsing: Slower than Node.js (~60x slower for CPU-heavy tasks)
- I/O operations: Good (async with asyncio)
- CPU-heavy tasks: Good (multiprocessing, Cython)

**Advantages:**
```
✓ Easiest to learn and develop
✓ Dominant in AI/ML (PyTorch, TensorFlow, scikit-learn)
✓ Excellent data processing libraries (Pandas, NumPy)
✓ Large talent pool (~30% of developers)
✓ Great for rapid prototyping
✓ Strong scientific computing ecosystem
✓ Type hints (since Python 3.5+)
```

**Disadvantages:**
```
✗ Slower than Node.js/Go/Rust (~60x slower than Rust for CPU tasks)
✗ GIL (Global Interpreter Lock) limits multi-threading
✗ Higher memory usage
✗ Async support still maturing
✗ Less suitable for high-performance APIs
```

**Best Use Cases:**
- AI/ML integration (pricing algorithms, recommendations)
- Data processing pipelines
- Admin dashboards
- Background jobs (data analysis, reporting)
- Rapid prototyping

**Salary Range (2025):**
- Junior: $70K-110K
- Mid: $110K-150K
- Senior: $150K-200K (higher for AI/ML specialists)

**Framework Recommendations:**

1. **Django** (Full-featured, batteries-included)
```python
# Pros: Admin panel, ORM, authentication, mature
# Cons: Monolithic, slower, opinionated

from django.http import JsonResponse
from .models import Resource

def list_resources(request):
    resources = Resource.objects.filter(**request.GET.dict())
    return JsonResponse(list(resources.values()), safe=False)
```

2. **FastAPI** (Modern, high-performance)
```python
# Pros: Fast (~3x faster than Django), async, automatic API docs, type validation
# Cons: Less batteries-included than Django

from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI()

@app.get("/api/resources")
async def list_resources(
    resource_type: str = Query(None),
    min_price: float = Query(None)
):
    resources = await Resource.find(resource_type, min_price)
    return resources
```

**Recommendation:** **FastAPI for APIs** (fast, modern), **Django for full web apps** (admin, ORM, auth built-in).

---

#### 3. Go (Golang)

**Performance Metrics (2025):**
- Request handling: ~20,000-50,000 req/sec per core
- JSON parsing: ~2x faster than Node.js
- I/O operations: Excellent (goroutines)
- CPU-heavy tasks: Excellent (compiled, efficient)

**Advantages:**
```
✓ Excellent performance (compiled, efficient garbage collection)
✓ Built-in concurrency (goroutines are lightweight)
✓ Fast compilation
✓ Single binary deployment (no dependencies)
✓ Great for microservices
✓ Strong standard library
✓ Good for DevOps tools (Docker, Kubernetes written in Go)
✓ Excellent error handling (explicit)
```

**Disadvantages:**
```
✗ More verbose than Node.js/Python
✗ Smaller ecosystem than Node.js/Python
✗ Less flexible (opinionated language design)
✗ Generics still maturing
✗ Smaller talent pool (~10-15% of developers)
```

**Best Use Cases:**
- High-performance APIs
- Microservices
- Real-time systems
- DevOps/infrastructure tools
- Network applications

**Salary Range (2025):**
- Junior: $80K-120K
- Mid: $120K-160K
- Senior: $160K-220K

**Framework Recommendations:**

1. **Gin** (High-performance web framework)
```go
// Pros: Fast, simple, middleware support, good docs
// Cons: Less opinionated than other frameworks

package main

import (
    "github.com/gin-gonic/gin"
    "net/http"
)

func main() {
    r := gin.Default()

    r.GET("/api/resources", func(c *gin.Context) {
        resources, err := FindResources(c.Query("type"))
        if err != nil {
            c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
            return
        }
        c.JSON(http.StatusOK, resources)
    })

    r.Run(":3000")
}
```

2. **Fiber** (Express-like API)
```go
// Pros: Very fast, Express-like syntax, easy migration from Node.js
// Cons: Smaller community than Gin

package main

import "github.com/gofiber/fiber/v2"

func main() {
    app := fiber.New()

    app.Get("/api/resources", func(c *fiber.Ctx) error {
        resources, err := FindResources(c.Query("type"))
        if err != nil {
            return c.Status(500).JSON(fiber.Map{"error": err.Error()})
        }
        return c.JSON(resources)
    })

    app.Listen(":3000")
}
```

**Recommendation:** **Go for high-performance microservices** where throughput and efficiency are critical.

---

#### 4. Rust

**Performance Metrics (2025):**
- Request handling: ~50,000-100,000 req/sec per core
- JSON parsing: ~60x faster than Python, ~2x faster than Go
- I/O operations: Excellent (async/await with tokio)
- CPU-heavy tasks: Excellent (zero-cost abstractions, no GC)

**Advantages:**
```
✓ Highest performance (memory-safe without garbage collection)
✓ Memory safety guaranteed by compiler
✓ Zero-cost abstractions
✓ Excellent for systems programming
✓ Growing web ecosystem (Actix, Axum, Rocket)
✓ No runtime overhead
✓ Fearless concurrency
```

**Disadvantages:**
```
✗ Steep learning curve (ownership, borrowing)
✗ Slower development speed initially
✗ Smaller ecosystem (but growing rapidly)
✗ Smallest talent pool (~5% of developers)
✗ Compile times can be slow
✗ More complex error handling
```

**Best Use Cases:**
- High-performance web services
- Systems programming
- Embedded systems
- Performance-critical microservices
- Cryptocurrency/blockchain (security critical)

**Salary Range (2025):**
- Junior: $90K-130K
- Mid: $130K-180K
- Senior: $180K-250K (highest premium)

**Framework Recommendations:**

1. **Axum** (Modern, Tokio-based)
```rust
// Pros: Fast, modern async, type-safe, growing ecosystem
// Cons: Still maturing, requires Rust expertise

use axum::{
    routing::get,
    Router,
    extract::Query,
    Json,
};

#[tokio::main]
async fn main() {
    let app = Router::new()
        .route("/api/resources", get(list_resources));

    axum::Server::bind(&"0.0.0.0:3000".parse().unwrap())
        .serve(app.into_make_service())
        .await
        .unwrap();
}

async fn list_resources(
    Query(params): Query<ResourceQuery>
) -> Json<Vec<Resource>> {
    let resources = find_resources(params).await;
    Json(resources)
}
```

2. **Actix-web** (Mature, proven)
```rust
// Pros: Very fast (1.5x faster than Go in benchmarks), mature, production-ready
// Cons: Steeper learning curve

use actix_web::{web, App, HttpServer, Result};

async fn list_resources(query: web::Query<ResourceQuery>) -> Result<web::Json<Vec<Resource>>> {
    let resources = find_resources(query.into_inner()).await?;
    Ok(web::Json(resources))
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    HttpServer::new(|| {
        App::new()
            .route("/api/resources", web::get().to(list_resources))
    })
    .bind(("0.0.0.0", 3000))?
    .run()
    .await
}
```

**Recommendation:** **Rust for performance-critical services** where memory safety and extreme performance justify the learning curve.

---

### Framework Selection Decision Tree

```
Start
  │
  ├─ Need extreme performance? (>50K req/sec/core)
  │   ├─ Yes → Rust (Axum/Actix)
  │   └─ No → Continue
  │
  ├─ AI/ML integration critical?
  │   ├─ Yes → Python (FastAPI)
  │   └─ No → Continue
  │
  ├─ Team has Go experience?
  │   ├─ Yes → Go (Gin/Fiber)
  │   └─ No → Continue
  │
  ├─ Need rapid development + large ecosystem?
  │   ├─ Yes → Node.js
  │   │   ├─ Enterprise app? → NestJS
  │   │   └─ Simple API? → Express
  │   └─ No → Go
  │
  └─ Default → Node.js (TypeScript) + NestJS
```

---

## Database Selection

### SQL vs NoSQL Comparison

| Feature | PostgreSQL | MongoDB | Redis | ElasticSearch |
|---------|------------|---------|-------|---------------|
| **Type** | SQL (Relational) | NoSQL (Document) | In-Memory KV | Search Engine |
| **Schema** | Rigid | Flexible | Schema-less | Flexible |
| **ACID** | Full | Limited (transactions since 4.0) | Partial | No |
| **Query** | SQL (complex joins) | MongoDB Query API | Key-value | Full-text search |
| **Performance** | Excellent (indexed) | Excellent (writes) | Fastest (in-memory) | Excellent (search) |
| **Scalability** | Vertical + Horizontal (sharding) | Horizontal (sharding) | Horizontal (cluster) | Horizontal |
| **Use Case** | Structured data, transactions | Flexible schemas, rapid iteration | Caching, sessions | Search, analytics |

### PostgreSQL (Recommended Primary Database)

**Why PostgreSQL:**
```
✓ Most admired database (Stack Overflow 2024, 2025)
✓ ACID compliance (data integrity)
✓ Excellent performance (10,000+ TPS)
✓ Advanced features (JSON, full-text search, GIS)
✓ Strong consistency
✓ Complex queries and joins
✓ Mature replication and backup
✓ Open source, no licensing costs
✓ Active development (new features regularly)
```

**Best For Marketplace:**
- User accounts (structured data)
- Resources (with relationships)
- Bookings (transactional)
- Financial records (ACID required)
- Reporting and analytics (complex queries)

**Schema Design Principles:**

```sql
-- 1. Normalization (reduce redundancy)
-- 2. Proper indexing (query performance)
-- 3. Foreign keys (referential integrity)
-- 4. Constraints (data validation)
-- 5. Partitioning (scale)

-- Example: Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(20) NOT NULL CHECK (role IN ('buyer', 'provider', 'admin')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP -- Soft delete
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_created_at ON users(created_at DESC);

-- Example: Resources table
CREATE TABLE resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID NOT NULL REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    resource_type VARCHAR(50) NOT NULL,
    specs JSONB NOT NULL, -- Flexible specs (CPU, RAM, GPU, etc.)
    price_per_hour DECIMAL(10, 2) NOT NULL,
    availability_status VARCHAR(20) NOT NULL DEFAULT 'available',
    location VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_resources_provider ON resources(provider_id);
CREATE INDEX idx_resources_type ON resources(resource_type);
CREATE INDEX idx_resources_price ON resources(price_per_hour);
CREATE INDEX idx_resources_specs ON resources USING GIN(specs); -- JSON index
```

**Advanced Features:**

1. **JSONB Support** (flexible data within structured schema)
```sql
-- Query JSON fields
SELECT *
FROM resources
WHERE specs->>'gpu' = 'NVIDIA RTX 4090'
  AND (specs->>'vram_gb')::int >= 24;

-- JSON indexing for fast queries
CREATE INDEX idx_resources_gpu ON resources ((specs->>'gpu'));
```

2. **Full-Text Search**
```sql
-- Add full-text search column
ALTER TABLE resources ADD COLUMN search_vector tsvector;

-- Generate search vector
UPDATE resources
SET search_vector = to_tsvector('english', name || ' ' || description);

-- Create GIN index
CREATE INDEX idx_resources_search ON resources USING GIN(search_vector);

-- Search query
SELECT *
FROM resources
WHERE search_vector @@ to_tsquery('english', 'GPU & machine & learning');
```

3. **Partitioning** (scale large tables)
```sql
-- Partition bookings by date (monthly)
CREATE TABLE bookings (
    id UUID,
    user_id UUID,
    resource_id UUID,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    status VARCHAR(20)
) PARTITION BY RANGE (start_time);

-- Create partitions
CREATE TABLE bookings_2025_01 PARTITION OF bookings
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE bookings_2025_02 PARTITION OF bookings
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- Automatic partition creation (use pg_partman extension)
```

4. **Replication** (read scaling)
```sql
-- Streaming replication (built-in)
-- Primary server: postgresql.conf
wal_level = replica
max_wal_senders = 3
wal_keep_size = 16MB

-- Replica server: recovery.conf
primary_conninfo = 'host=primary.example.com port=5432 user=replicator password=...'
```

**Connection Pooling:**
```javascript
// Use connection pooler (PgBouncer or built-in pg.Pool)
const { Pool } = require('pg');

const pool = new Pool({
  host: 'localhost',
  port: 5432,
  database: 'marketplace',
  user: 'app_user',
  password: process.env.DB_PASSWORD,
  max: 20, // Maximum 20 connections in pool
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});

// Reusable query function
async function query(text, params) {
  const start = Date.now();
  const res = await pool.query(text, params);
  const duration = Date.now() - start;
  console.log('Executed query', { text, duration, rows: res.rowCount });
  return res;
}
```

---

### MongoDB (Optional Complementary Database)

**When to Use MongoDB:**
```
✓ Rapidly changing schema (early-stage product)
✓ Document-oriented data (logs, events)
✓ High write throughput (IoT data, clickstreams)
✓ Flexible product catalogs (varying attributes)
✓ Content management (blog posts, comments)
```

**Example Use Cases in Marketplace:**
- Activity logs (user actions, resource usage)
- Analytics events (page views, clicks)
- Notification history
- Temporary data (shopping cart, sessions)

**Schema Design:**

```javascript
// Users collection (denormalized)
{
  _id: ObjectId("..."),
  email: "user@example.com",
  profile: {
    firstName: "John",
    lastName: "Doe",
    avatar: "https://..."
  },
  role: "provider",
  resources: [ // Embedded documents
    {
      resourceId: "res_123",
      name: "GPU Server",
      status: "available"
    }
  ],
  createdAt: ISODate("2025-01-15T10:30:00Z"),
  updatedAt: ISODate("2025-01-15T10:30:00Z")
}

// Activity logs collection
{
  _id: ObjectId("..."),
  userId: "user_123",
  action: "resource_view",
  resourceId: "res_456",
  metadata: {
    ip: "192.168.1.1",
    userAgent: "Mozilla/5.0...",
    duration: 1250
  },
  timestamp: ISODate("2025-01-15T10:30:00Z")
}
```

**Indexing:**
```javascript
// Create indexes
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ role: 1 });
db.activityLogs.createIndex({ userId: 1, timestamp: -1 });
db.activityLogs.createIndex({ timestamp: -1 }, { expireAfterSeconds: 2592000 }); // TTL: 30 days
```

**Aggregation Pipeline:**
```javascript
// Complex analytics query
db.activityLogs.aggregate([
  { $match: { action: "resource_view", timestamp: { $gte: ISODate("2025-01-01") } } },
  { $group: { _id: "$resourceId", views: { $sum: 1 } } },
  { $sort: { views: -1 } },
  { $limit: 10 }
]);
```

---

### Redis (Highly Recommended for Caching)

**Use Cases:**
```
✓ Session storage (JWT tokens, user sessions)
✓ Caching database queries (hot data)
✓ Rate limiting (API throttling)
✓ Real-time data (online users, leaderboards)
✓ Pub/Sub (real-time notifications)
✓ Queue (job processing with Bull)
```

**Performance:**
- 100,000+ operations per second per node
- Sub-millisecond latency
- Supports complex data structures (strings, hashes, lists, sets, sorted sets)

---

## Caching Strategy

### Cache Hierarchy

```
┌──────────────────────────────────────────┐
│        Client (Browser Cache)            │ ← Static assets (CSS, JS, images)
└──────────────────────────────────────────┘
                  │
┌──────────────────────────────────────────┐
│           CDN (CloudFront)               │ ← Static assets, API responses (short TTL)
└──────────────────────────────────────────┘
                  │
┌──────────────────────────────────────────┐
│      Application Cache (Redis)           │ ← Database queries, session data
└──────────────────────────────────────────┘
                  │
┌──────────────────────────────────────────┐
│      Database (PostgreSQL)               │ ← Source of truth
└──────────────────────────────────────────┘
```

### Redis Implementation

**1. Query Result Caching:**

```javascript
const redis = require('redis');
const client = redis.createClient();

async function getResource(id) {
  const cacheKey = `resource:${id}`;

  // Try cache first
  const cached = await client.get(cacheKey);
  if (cached) {
    console.log('Cache hit');
    return JSON.parse(cached);
  }

  // Cache miss, query database
  console.log('Cache miss');
  const resource = await db.query('SELECT * FROM resources WHERE id = $1', [id]);

  // Store in cache (TTL: 1 hour)
  await client.setEx(cacheKey, 3600, JSON.stringify(resource));

  return resource;
}
```

**2. Cache Invalidation:**

```javascript
// Invalidate on update
async function updateResource(id, data) {
  // Update database
  await db.query('UPDATE resources SET ... WHERE id = $1', [id]);

  // Invalidate cache
  await client.del(`resource:${id}`);

  // Optionally, update cache immediately
  const updated = await db.query('SELECT * FROM resources WHERE id = $1', [id]);
  await client.setEx(`resource:${id}`, 3600, JSON.stringify(updated));
}
```

**3. Rate Limiting:**

```javascript
async function rateLimit(userId, limit = 100, window = 60) {
  const key = `rate_limit:${userId}`;
  const current = await client.incr(key);

  if (current === 1) {
    await client.expire(key, window); // Set expiry on first request
  }

  if (current > limit) {
    throw new Error('Rate limit exceeded');
  }

  return { remaining: limit - current, resetIn: await client.ttl(key) };
}
```

**4. Session Management:**

```javascript
// Store user session
async function createSession(userId, data) {
  const sessionId = crypto.randomUUID();
  const key = `session:${sessionId}`;

  await client.setEx(key, 86400, JSON.stringify({ userId, ...data })); // 24 hours

  return sessionId;
}

// Retrieve session
async function getSession(sessionId) {
  const key = `session:${sessionId}`;
  const session = await client.get(key);

  return session ? JSON.parse(session) : null;
}
```

**5. Pub/Sub for Real-Time:**

```javascript
// Publisher (when resource status changes)
async function notifyResourceUpdate(resourceId, status) {
  await client.publish('resource_updates', JSON.stringify({ resourceId, status }));
}

// Subscriber (WebSocket server listens)
const subscriber = redis.createClient();
subscriber.subscribe('resource_updates', (message) => {
  const { resourceId, status } = JSON.parse(message);
  // Send WebSocket message to connected clients
  io.to(`resource:${resourceId}`).emit('status_update', status);
});
```

---

## Message Queues & Background Jobs

### Why Message Queues?

```
✓ Asynchronous processing (don't block API responses)
✓ Reliability (retry failed jobs)
✓ Load balancing (distribute work across workers)
✓ Decoupling (separate services)
✓ Scalability (add more workers)
```

### RabbitMQ vs Redis (Bull) vs AWS SQS

| Feature | RabbitMQ | Redis (Bull) | AWS SQS |
|---------|----------|--------------|---------|
| **Performance** | High | Very High | High |
| **Reliability** | Excellent | Good | Excellent |
| **Features** | Rich (routing, exchanges) | Simple | Moderate |
| **Complexity** | Moderate | Low | Low |
| **Scaling** | Horizontal | Horizontal | Automatic |
| **Cost** | Self-hosted | Self-hosted | Pay-per-use |

**Recommendation:** **RabbitMQ for complex workflows**, **Bull (Redis) for simple jobs**, **AWS SQS for serverless/managed**.

### Bull (Redis-based) Implementation

```javascript
const Queue = require('bull');

// Create queue
const emailQueue = new Queue('email', {
  redis: { host: 'localhost', port: 6379 }
});

// Producer: Add job to queue
async function sendWelcomeEmail(userId) {
  await emailQueue.add('welcome', { userId }, {
    attempts: 3, // Retry 3 times on failure
    backoff: { type: 'exponential', delay: 2000 } // 2s, 4s, 8s
  });
}

// Consumer: Process jobs
emailQueue.process('welcome', async (job) => {
  const { userId } = job.data;

  const user = await getUserById(userId);
  await sendEmail(user.email, 'Welcome!', welcomeTemplate(user));

  return { sent: true, email: user.email };
});

// Job lifecycle events
emailQueue.on('completed', (job, result) => {
  console.log(`Job ${job.id} completed:`, result);
});

emailQueue.on('failed', (job, err) => {
  console.error(`Job ${job.id} failed:`, err);
});
```

### RabbitMQ Implementation

```javascript
const amqp = require('amqplib');

// Producer
async function publishJob(queueName, data) {
  const connection = await amqp.connect('amqp://localhost');
  const channel = await connection.createChannel();

  await channel.assertQueue(queueName, { durable: true });
  channel.sendToQueue(queueName, Buffer.from(JSON.stringify(data)), {
    persistent: true
  });

  await channel.close();
  await connection.close();
}

// Consumer
async function consumeJobs(queueName, handler) {
  const connection = await amqp.connect('amqp://localhost');
  const channel = await connection.createChannel();

  await channel.assertQueue(queueName, { durable: true });
  channel.prefetch(1); // Process one job at a time

  channel.consume(queueName, async (msg) => {
    const data = JSON.parse(msg.content.toString());

    try {
      await handler(data);
      channel.ack(msg); // Acknowledge successful processing
    } catch (error) {
      console.error('Job failed:', error);
      channel.nack(msg, false, true); // Requeue on failure
    }
  });
}

// Usage
await publishJob('email', { userId: '123', type: 'welcome' });

consumeJobs('email', async (data) => {
  await sendEmail(data);
});
```

### Common Background Jobs

```javascript
// 1. Email notifications
emailQueue.add('booking_confirmation', { bookingId, userId });

// 2. Analytics processing
analyticsQueue.add('process_events', { events, timestamp });

// 3. Resource cleanup
cleanupQueue.add('delete_expired_sessions', {}, {
  repeat: { cron: '0 * * * *' } // Every hour
});

// 4. Report generation
reportQueue.add('generate_monthly_report', { userId, month }, {
  priority: 5, // Lower priority
  timeout: 300000 // 5 minutes
});

// 5. Image processing
imageQueue.add('optimize_image', { imageUrl, sizes: [100, 300, 600] });
```

---

## Recommended Stack

### Primary Recommendation

**Stack:** Node.js (TypeScript) + NestJS + PostgreSQL + Redis + Bull

**Rationale:**
1. **Node.js (TypeScript)**: Best balance of performance, productivity, and ecosystem
2. **NestJS**: Enterprise-grade structure, dependency injection, testing
3. **PostgreSQL**: Best SQL database, ACID compliance, JSON support
4. **Redis**: Caching, sessions, rate limiting, pub/sub
5. **Bull**: Simple job queue backed by Redis

**Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│                      Client (React/Vue)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────────┐
│                  Load Balancer (NGINX)                      │
└──────────────────────┬──────────────────────────────────────┘
          ┌────────────┼────────────┐
          │            │            │
┌─────────▼──┐  ┌──────▼────┐  ┌───▼─────────┐
│ NestJS API │  │NestJS API │  │ NestJS API  │
│  Server 1  │  │ Server 2  │  │  Server N   │
└─────────┬──┘  └──────┬────┘  └───┬─────────┘
          │            │            │
          └────────────┼────────────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
┌─────────▼──────┐ ┌──▼─────────┐ ┌▼────────────┐
│  PostgreSQL    │ │   Redis    │ │  RabbitMQ   │
│  (Primary)     │ │  (Cache)   │ │  (Queue)    │
└────────┬───────┘ └────────────┘ └─────────────┘
         │
┌────────▼───────┐
│  PostgreSQL    │
│  (Read Replica)│
└────────────────┘
```

### Alternative Stacks

**For AI/ML Integration:**
- **Stack**: Python (FastAPI) + PostgreSQL + Redis + Celery
- **Rationale**: Python dominates AI/ML, FastAPI is fast and modern

**For Extreme Performance:**
- **Stack**: Rust (Axum) + PostgreSQL + Redis
- **Rationale**: Maximum performance, memory safety

**For Rapid Prototyping:**
- **Stack**: Python (Django) + PostgreSQL
- **Rationale**: Fastest time-to-market, batteries included

---

## Project Structure

### NestJS Project Structure (Recommended)

```
compute-marketplace/
├── src/
│   ├── main.ts                    # Application entry point
│   ├── app.module.ts              # Root module
│   │
│   ├── config/                    # Configuration
│   │   ├── database.config.ts
│   │   ├── redis.config.ts
│   │   └── jwt.config.ts
│   │
│   ├── common/                    # Shared utilities
│   │   ├── decorators/
│   │   ├── filters/               # Exception filters
│   │   ├── guards/                # Auth guards
│   │   ├── interceptors/          # Logging, transform
│   │   ├── pipes/                 # Validation pipes
│   │   └── middleware/
│   │
│   ├── modules/
│   │   ├── auth/                  # Authentication module
│   │   │   ├── auth.controller.ts
│   │   │   ├── auth.service.ts
│   │   │   ├── auth.module.ts
│   │   │   ├── dto/
│   │   │   │   ├── login.dto.ts
│   │   │   │   └── register.dto.ts
│   │   │   ├── strategies/
│   │   │   │   ├── jwt.strategy.ts
│   │   │   │   └── local.strategy.ts
│   │   │   └── guards/
│   │   │       ├── jwt-auth.guard.ts
│   │   │       └── roles.guard.ts
│   │   │
│   │   ├── users/                 # User module
│   │   │   ├── users.controller.ts
│   │   │   ├── users.service.ts
│   │   │   ├── users.module.ts
│   │   │   ├── entities/
│   │   │   │   └── user.entity.ts
│   │   │   ├── dto/
│   │   │   │   ├── create-user.dto.ts
│   │   │   │   └── update-user.dto.ts
│   │   │   └── repositories/
│   │   │       └── user.repository.ts
│   │   │
│   │   ├── resources/             # Resource module
│   │   │   ├── resources.controller.ts
│   │   │   ├── resources.service.ts
│   │   │   ├── resources.module.ts
│   │   │   ├── entities/
│   │   │   │   └── resource.entity.ts
│   │   │   ├── dto/
│   │   │   └── repositories/
│   │   │
│   │   ├── bookings/              # Booking module
│   │   │   ├── bookings.controller.ts
│   │   │   ├── bookings.service.ts
│   │   │   ├── bookings.module.ts
│   │   │   ├── entities/
│   │   │   ├── dto/
│   │   │   └── repositories/
│   │   │
│   │   ├── payments/              # Payment module
│   │   │   ├── payments.controller.ts
│   │   │   ├── payments.service.ts
│   │   │   ├── payments.module.ts
│   │   │   └── processors/
│   │   │       ├── stripe.processor.ts
│   │   │       └── crypto.processor.ts
│   │   │
│   │   ├── notifications/         # Notification module
│   │   │   ├── notifications.service.ts
│   │   │   ├── notifications.module.ts
│   │   │   └── channels/
│   │   │       ├── email.channel.ts
│   │   │       ├── sms.channel.ts
│   │   │       └── push.channel.ts
│   │   │
│   │   └── analytics/             # Analytics module
│   │       ├── analytics.controller.ts
│   │       ├── analytics.service.ts
│   │       └── analytics.module.ts
│   │
│   ├── database/                  # Database related
│   │   ├── migrations/
│   │   ├── seeds/
│   │   └── database.module.ts
│   │
│   ├── queues/                    # Background jobs
│   │   ├── email.queue.ts
│   │   ├── analytics.queue.ts
│   │   └── cleanup.queue.ts
│   │
│   └── utils/                     # Utility functions
│       ├── logger.ts
│       ├── crypto.ts
│       └── validators.ts
│
├── test/                          # E2E tests
│   ├── app.e2e-spec.ts
│   └── ...
│
├── .env                           # Environment variables
├── .env.example
├── .eslintrc.js
├── .prettierrc
├── nest-cli.json
├── package.json
├── tsconfig.json
└── README.md
```

---

## Code Examples

### Complete NestJS Module Example

**1. Entity (User)**

```typescript
// src/modules/users/entities/user.entity.ts
import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
  UpdateDateColumn,
  OneToMany,
} from 'typeorm';
import { Exclude } from 'class-transformer';
import { Resource } from '../../resources/entities/resource.entity';

@Entity('users')
export class User {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ unique: true })
  email: string;

  @Column()
  @Exclude() // Don't expose password in API responses
  passwordHash: string;

  @Column()
  firstName: string;

  @Column()
  lastName: string;

  @Column({ type: 'enum', enum: ['buyer', 'provider', 'admin'] })
  role: string;

  @Column({ default: true })
  isActive: boolean;

  @OneToMany(() => Resource, (resource) => resource.provider)
  resources: Resource[];

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;

  @Column({ nullable: true })
  deletedAt?: Date;
}
```

**2. DTO (Data Transfer Object)**

```typescript
// src/modules/users/dto/create-user.dto.ts
import { IsEmail, IsString, MinLength, IsEnum } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class CreateUserDto {
  @ApiProperty({ example: 'user@example.com' })
  @IsEmail()
  email: string;

  @ApiProperty({ example: 'SecurePassword123!' })
  @IsString()
  @MinLength(8)
  password: string;

  @ApiProperty({ example: 'John' })
  @IsString()
  firstName: string;

  @ApiProperty({ example: 'Doe' })
  @IsString()
  lastName: string;

  @ApiProperty({ example: 'buyer', enum: ['buyer', 'provider'] })
  @IsEnum(['buyer', 'provider'])
  role: string;
}
```

**3. Service (Business Logic)**

```typescript
// src/modules/users/users.service.ts
import { Injectable, NotFoundException, ConflictException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import * as bcrypt from 'bcrypt';
import { User } from './entities/user.entity';
import { CreateUserDto } from './dto/create-user.dto';
import { UpdateUserDto } from './dto/update-user.dto';

@Injectable()
export class UsersService {
  constructor(
    @InjectRepository(User)
    private usersRepository: Repository<User>,
  ) {}

  async create(createUserDto: CreateUserDto): Promise<User> {
    // Check if user exists
    const existingUser = await this.usersRepository.findOne({
      where: { email: createUserDto.email },
    });

    if (existingUser) {
      throw new ConflictException('User with this email already exists');
    }

    // Hash password
    const passwordHash = await bcrypt.hash(createUserDto.password, 10);

    // Create user
    const user = this.usersRepository.create({
      ...createUserDto,
      passwordHash,
    });

    return this.usersRepository.save(user);
  }

  async findAll(page: number = 1, limit: number = 10): Promise<{ data: User[]; total: number }> {
    const [data, total] = await this.usersRepository.findAndCount({
      skip: (page - 1) * limit,
      take: limit,
      order: { createdAt: 'DESC' },
    });

    return { data, total };
  }

  async findOne(id: string): Promise<User> {
    const user = await this.usersRepository.findOne({
      where: { id },
      relations: ['resources'],
    });

    if (!user) {
      throw new NotFoundException(`User with ID ${id} not found`);
    }

    return user;
  }

  async findByEmail(email: string): Promise<User | null> {
    return this.usersRepository.findOne({ where: { email } });
  }

  async update(id: string, updateUserDto: UpdateUserDto): Promise<User> {
    const user = await this.findOne(id);

    Object.assign(user, updateUserDto);

    return this.usersRepository.save(user);
  }

  async remove(id: string): Promise<void> {
    const user = await this.findOne(id);

    // Soft delete
    user.deletedAt = new Date();
    await this.usersRepository.save(user);
  }
}
```

**4. Controller (API Endpoints)**

```typescript
// src/modules/users/users.controller.ts
import {
  Controller,
  Get,
  Post,
  Body,
  Patch,
  Param,
  Delete,
  Query,
  UseGuards,
  HttpCode,
  HttpStatus,
} from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';
import { UsersService } from './users.service';
import { CreateUserDto } from './dto/create-user.dto';
import { UpdateUserDto } from './dto/update-user.dto';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { RolesGuard } from '../auth/guards/roles.guard';
import { Roles } from '../auth/decorators/roles.decorator';

@ApiTags('users')
@Controller('api/v1/users')
export class UsersController {
  constructor(private readonly usersService: UsersService) {}

  @Post()
  @ApiOperation({ summary: 'Create a new user' })
  @ApiResponse({ status: 201, description: 'User created successfully' })
  @ApiResponse({ status: 409, description: 'User already exists' })
  async create(@Body() createUserDto: CreateUserDto) {
    return this.usersService.create(createUserDto);
  }

  @Get()
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles('admin')
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Get all users (admin only)' })
  async findAll(
    @Query('page') page: number = 1,
    @Query('limit') limit: number = 10,
  ) {
    return this.usersService.findAll(page, limit);
  }

  @Get(':id')
  @UseGuards(JwtAuthGuard)
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Get user by ID' })
  @ApiResponse({ status: 200, description: 'User found' })
  @ApiResponse({ status: 404, description: 'User not found' })
  async findOne(@Param('id') id: string) {
    return this.usersService.findOne(id);
  }

  @Patch(':id')
  @UseGuards(JwtAuthGuard)
  @ApiBearerAuth()
  @ApiOperation({ summary: 'Update user' })
  async update(
    @Param('id') id: string,
    @Body() updateUserDto: UpdateUserDto,
  ) {
    return this.usersService.update(id, updateUserDto);
  }

  @Delete(':id')
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles('admin')
  @ApiBearerAuth()
  @HttpCode(HttpStatus.NO_CONTENT)
  @ApiOperation({ summary: 'Delete user (admin only)' })
  async remove(@Param('id') id: string) {
    return this.usersService.remove(id);
  }
}
```

**5. Module (Wire Everything Together)**

```typescript
// src/modules/users/users.module.ts
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { UsersController } from './users.controller';
import { UsersService } from './users.service';
import { User } from './entities/user.entity';

@Module({
  imports: [TypeOrmModule.forFeature([User])],
  controllers: [UsersController],
  providers: [UsersService],
  exports: [UsersService], // Export for use in other modules
})
export class UsersModule {}
```

**6. Authentication (JWT)**

```typescript
// src/modules/auth/auth.service.ts
import { Injectable, UnauthorizedException } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import * as bcrypt from 'bcrypt';
import { UsersService } from '../users/users.service';

@Injectable()
export class AuthService {
  constructor(
    private usersService: UsersService,
    private jwtService: JwtService,
  ) {}

  async validateUser(email: string, password: string): Promise<any> {
    const user = await this.usersService.findByEmail(email);

    if (!user) {
      throw new UnauthorizedException('Invalid credentials');
    }

    const isPasswordValid = await bcrypt.compare(password, user.passwordHash);

    if (!isPasswordValid) {
      throw new UnauthorizedException('Invalid credentials');
    }

    const { passwordHash, ...result } = user;
    return result;
  }

  async login(user: any) {
    const payload = { email: user.email, sub: user.id, role: user.role };

    return {
      access_token: this.jwtService.sign(payload),
      user,
    };
  }

  async register(createUserDto: any) {
    const user = await this.usersService.create(createUserDto);
    return this.login(user);
  }
}
```

**7. Main Application**

```typescript
// src/main.ts
import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Enable CORS
  app.enableCors({
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
    credentials: true,
  });

  // Global validation pipe
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true, // Strip unknown properties
      forbidNonWhitelisted: true, // Throw error on unknown properties
      transform: true, // Transform payloads to DTO instances
    }),
  );

  // Swagger API documentation
  const config = new DocumentBuilder()
    .setTitle('Compute Marketplace API')
    .setDescription('API for compute resource marketplace')
    .setVersion('1.0')
    .addBearerAuth()
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('api/docs', app, document);

  await app.listen(3000);
  console.log(`Application is running on: http://localhost:3000`);
  console.log(`API docs available at: http://localhost:3000/api/docs`);
}

bootstrap();
```

---

## Deployment Considerations

### Environment Configuration

```bash
# .env
NODE_ENV=production
PORT=3000

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=marketplace
DB_USER=app_user
DB_PASSWORD=secure_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# JWT
JWT_SECRET=your_secret_key_here
JWT_EXPIRY=15m

# External services
STRIPE_API_KEY=sk_live_...
AWS_S3_BUCKET=marketplace-files
AWS_REGION=us-east-1

# Frontend
FRONTEND_URL=https://marketplace.example.com
```

### Docker Configuration

```dockerfile
# Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY --from=builder /app/dist ./dist

EXPOSE 3000

CMD ["node", "dist/main"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DB_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: marketplace
      POSTGRES_USER: app_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Health Checks

```typescript
// src/health/health.controller.ts
import { Controller, Get } from '@nestjs/common';
import { HealthCheck, HealthCheckService, TypeOrmHealthIndicator } from '@nestjs/terminus';

@Controller('health')
export class HealthController {
  constructor(
    private health: HealthCheckService,
    private db: TypeOrmHealthIndicator,
  ) {}

  @Get()
  @HealthCheck()
  check() {
    return this.health.check([
      () => this.db.pingCheck('database'),
    ]);
  }
}
```

---

## Conclusion

**Final Recommendation:**

```
Language: Node.js (TypeScript)
Framework: NestJS
Database: PostgreSQL
Cache: Redis
Queue: Bull (Redis-based)
```

This stack offers the best balance of:
- Developer productivity
- Performance
- Ecosystem maturity
- Team availability
- Cost-effectiveness
- Scalability

**Next Steps:**
1. Set up project structure using NestJS CLI
2. Configure PostgreSQL with proper schema design
3. Implement Redis caching layer
4. Set up Bull for background jobs
5. Add comprehensive testing
6. Deploy with Docker and Kubernetes

---

**Document Version**: 1.0
**Last Updated**: 2025-10-14
**Author**: Backend Architecture Team
