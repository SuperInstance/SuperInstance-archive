

# Swarm Intelligence Platform - API & Integration Documentation

## Overview

Complete API and integration system for the Swarm Intelligence Platform, providing universal access through REST, GraphQL, WebSocket, and SDKs in multiple languages.

## Table of Contents

1. [REST API](#rest-api)
2. [GraphQL API](#graphql-api)
3. [WebSocket API](#websocket-api)
4. [SDKs](#sdks)
5. [No-Code Integrations](#no-code-integrations)
6. [Authentication](#authentication)
7. [Rate Limiting](#rate-limiting)
8. [Examples](#examples)

---

## REST API

### Base URL
```
Production: https://api.swarm.dev
Staging: https://staging-api.swarm.dev
```

### Endpoints

#### Swarm Management

**Create Swarm**
```http
POST /api/v1/swarms
Authorization: Bearer YOUR_API_KEY

{
  "name": "my-swarm",
  "agent_count": 10,
  "agent_type": "WORKER",
  "config": {
    "coordination_protocol": "democratic",
    "voting_threshold": 0.7,
    "pheromone_enabled": true
  }
}
```

**Get Swarm**
```http
GET /api/v1/swarms/{swarm_id}
```

**List Swarms**
```http
GET /api/v1/swarms?status=RUNNING&limit=20&offset=0
```

**Scale Swarm**
```http
PATCH /api/v1/swarms/{swarm_id}/scale
{
  "agent_count": 25
}
```

**Terminate Swarm**
```http
DELETE /api/v1/swarms/{swarm_id}
```

#### Task Management

**Submit Task**
```http
POST /api/v1/swarms/{swarm_id}/tasks
{
  "type": "code_review",
  "payload": {
    "repository": "github.com/user/repo",
    "files": ["main.py"]
  },
  "priority": "HIGH",
  "timeout": 300
}
```

**Get Task Status**
```http
GET /api/v1/tasks/{task_id}
```

**List Tasks**
```http
GET /api/v1/swarms/{swarm_id}/tasks?status=COMPLETED&limit=50
```

#### Metrics & Monitoring

**Get Metrics**
```http
GET /api/v1/swarms/{swarm_id}/metrics?window=LAST_HOUR
```

**Stream Metrics (SSE)**
```http
GET /api/v1/swarms/{swarm_id}/metrics/stream
```

#### Creative Production

**Batch Processing**
```http
POST /api/v1/creative/batch
{
  "swarm_id": "swarm_abc123",
  "tasks": [
    {"type": "image_gen", "payload": {"prompt": "sunset"}},
    {"type": "image_gen", "payload": {"prompt": "ocean"}}
  ]
}
```

**Streaming Generation**
```http
POST /api/v1/creative/stream
{
  "swarm_id": "swarm_abc123",
  "task_type": "video_generation",
  "payload": {"script": "..."}
}
```

#### Webhooks

**Register Webhook**
```http
POST /api/v1/webhooks
{
  "url": "https://your-app.com/webhook",
  "events": ["task.completed", "swarm.error"],
  "secret": "your-webhook-secret"
}
```

---

## GraphQL API

### Endpoint
```
https://api.swarm.dev/graphql
```

### Example Queries

**Get Swarm with Nested Data**
```graphql
query {
  swarm(id: "swarm_abc123") {
    id
    name
    status
    agents {
      id
      status
      capabilities
      performanceScore
    }
    metrics {
      tasksCompleted
      agentUtilization
      errorRate
    }
    tasks(status: COMPLETED, limit: 10) {
      id
      type
      result
      completedAt
    }
  }
}
```

**Create Swarm and Submit Task**
```graphql
mutation {
  createSwarm(input: {
    name: "creative-swarm"
    agentCount: 50
    agentType: WORKER
    config: {
      coordinationProtocol: "democratic"
      pheromoneEnabled: true
    }
  }) {
    id
    status
    agents {
      id
    }
  }

  submitTask(input: {
    swarmId: "swarm_abc123"
    type: "image_generation"
    payload: {prompt: "futuristic city"}
    priority: HIGH
  }) {
    id
    status
  }
}
```

**Subscribe to Real-Time Updates**
```graphql
subscription {
  swarmStatus(swarmId: "swarm_abc123") {
    id
    status
    metrics {
      tasksCompleted
      agentUtilization
    }
  }
}
```

---

## WebSocket API

### Connection
```javascript
const ws = new WebSocket('wss://api.swarm.dev/ws/swarm_abc123');

// Authenticate
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    api_key: 'YOUR_API_KEY'
  }));
};

// Subscribe to events
ws.send(JSON.stringify({
  type: 'subscribe',
  events: ['agent_status', 'task_progress', 'metrics']
}));

// Handle messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

### Events
- `agent_status`: Agent state changes
- `task_progress`: Task completion updates
- `metrics`: Real-time metrics
- `errors`: Error notifications

---

## SDKs

### Python SDK

**Installation**
```bash
pip install swarm-intelligence
```

**Usage**
```python
from swarm_intelligence import SwarmClient, AgentType

# Initialize client
client = SwarmClient(api_key="your-api-key")

# Create swarm
swarm = client.create_swarm(
    name="python-swarm",
    agent_count=10,
    agent_type=AgentType.WORKER
)

# Submit task
task = swarm.submit_task(
    type="process",
    payload={"data": "example"}
)

# Wait for result
result = task.wait_for_completion()
print(result)

# Cleanup
swarm.terminate()
```

**Async Support**
```python
from swarm_intelligence import AsyncSwarmClient

async def main():
    async with AsyncSwarmClient(api_key="your-key") as client:
        swarm = await client.create_swarm(name="async-swarm")
        task = await swarm.submit_task(type="process", payload={})
        result = await task.wait_for_completion()
        print(result)

import asyncio
asyncio.run(main())
```

### JavaScript/TypeScript SDK

**Installation**
```bash
npm install @swarm-intelligence/sdk
```

**Usage**
```typescript
import { SwarmClient, AgentType } from '@swarm-intelligence/sdk';

const client = new SwarmClient({
  apiKey: 'your-api-key'
});

// Create swarm
const swarm = await client.createSwarm({
  name: 'js-swarm',
  agentCount: 10,
  agentType: AgentType.WORKER
});

// Submit task
const task = await swarm.submitTask({
  type: 'process',
  payload: { data: 'example' }
});

// Wait for result
const result = await task.waitForCompletion();
console.log(result);
```

**React Hooks**
```typescript
import { useSwarm, useTask } from '@swarm-intelligence/react';

function MyComponent() {
  const { swarm, loading } = useSwarm({
    name: 'react-swarm',
    agentCount: 5
  });

  const { submitTask, tasks } = useTask(swarm);

  const handleSubmit = async () => {
    const task = await submitTask({
      type: 'process',
      payload: { data: 'test' }
    });
  };

  return (
    <div>
      <h2>Swarm Status: {swarm?.status}</h2>
      <button onClick={handleSubmit}>Submit Task</button>
    </div>
  );
}
```

### Go SDK

**Installation**
```bash
go get github.com/swarm-intelligence/go-sdk
```

**Usage**
```go
package main

import (
    "context"
    "fmt"
    swarm "github.com/swarm-intelligence/go-sdk"
)

func main() {
    client := swarm.NewClient("your-api-key")
    ctx := context.Background()

    // Create swarm
    s, err := client.CreateSwarm(ctx, swarm.CreateSwarmParams{
        Name:       "go-swarm",
        AgentCount: 10,
        AgentType:  swarm.AgentTypeWorker,
    })
    if err != nil {
        panic(err)
    }
    defer s.Terminate(ctx)

    // Submit task
    task, err := s.SubmitTask(ctx, swarm.TaskParams{
        Type: "process",
        Payload: map[string]interface{}{
            "data": "example",
        },
    })

    // Wait for result
    result, err := task.WaitForCompletion(ctx)
    fmt.Printf("Result: %v\n", result)
}
```

---

## No-Code Integrations

### Zapier

**Available Triggers**
- Task Completed
- Swarm Error
- Agent Failed
- Metrics Threshold Exceeded
- Creative Output Ready

**Available Actions**
- Create Swarm
- Submit Task
- Scale Swarm
- Terminate Swarm
- Generate Creative Content

**Example Workflow**
```
Trigger: New row in Google Sheets
Action: Create Swarm → Submit Task → Send Slack notification
```

### Microsoft Power Automate

**Connector Features**
- All REST API endpoints
- Real-time webhooks
- Pre-built templates

**Example Flow**
```
When form submitted → Create swarm → Process data → Save to SharePoint
```

### Slack Bot

**Commands**
- `/swarm-create name=my-swarm agents=10`
- `/swarm-status swarm_abc123`
- `/swarm-task swarm_abc123 type=process`

**Natural Language**
```
@swarmbot create a swarm with 20 workers
@swarmbot show me the status of swarm_abc123
@swarmbot submit a rendering task
```

### Discord Bot

**Commands**
- `!swarm create <name> <count>`
- `!swarm status <id>`
- `!swarm task <id> <type>`

**Gaming Features**
- Procedural content generation
- NPC behavior coordination
- Quest generation
- Real-time game metrics

---

## Authentication

### API Keys
```bash
# Get API key via dashboard or API
curl -X POST https://api.swarm.dev/api/v1/auth/api-key \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'
```

### OAuth 2.0
```bash
# Get access token
curl -X POST https://api.swarm.dev/api/v1/auth/token \
  -d "username=user&password=pass&grant_type=password"
```

### Usage
```bash
# With API key
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.swarm.dev/api/v1/swarms
```

---

## Rate Limiting

### Tiers

| Tier | Requests/Min | Concurrent Swarms | Total Agents |
|------|-------------|-------------------|--------------|
| Free | 60 | 3 | 30 |
| Pro | 600 | 20 | 500 |
| Team | 3000 | 100 | 5000 |
| Enterprise | Unlimited | Unlimited | Unlimited |

### Headers
```
X-RateLimit-Limit: 600
X-RateLimit-Remaining: 594
X-RateLimit-Reset: 1634212860
```

---

## Examples

### Example 1: Batch Image Processing

**Python**
```python
client = SwarmClient(api_key="key")
swarm = client.create_swarm("image-processor", agent_count=50)

# Submit batch
tasks = []
for image_url in image_urls:
    task = swarm.submit_task(
        type="image_process",
        payload={"url": image_url, "filter": "enhance"}
    )
    tasks.append(task)

# Wait for all
results = [task.wait_for_completion() for task in tasks]
```

### Example 2: Real-Time Creative Generation

**JavaScript**
```javascript
const swarm = await client.createSwarm({
  name: 'creative-swarm',
  agentCount: 100
});

// Stream generation
const stream = await swarm.streamCreativeGeneration({
  type: 'art',
  prompt: 'abstract painting'
});

for await (const chunk of stream) {
  displayPartialImage(chunk);
}
```

### Example 3: Automated Workflow via Zapier

```
Trigger: New lead in CRM
↓
Action 1: Create swarm with 10 agents
↓
Action 2: Submit personalization task
↓
Action 3: Wait for completion (webhook)
↓
Action 4: Send personalized email
↓
Action 5: Terminate swarm
```

### Example 4: Game NPC System

**Go**
```go
// Create NPC swarm
npcSwarm, _ := client.CreateSwarm(ctx, swarm.CreateSwarmParams{
    Name:       "npc-behaviors",
    AgentCount: 200,
    AgentType:  swarm.AgentTypeWorker,
})

// Continuous NPC decision-making
for {
    gameState := getGameState()

    // Submit NPC behavior tasks
    for _, npc := range gameState.NPCs {
        npcSwarm.SubmitTask(ctx, swarm.TaskParams{
            Type: "npc_decision",
            Payload: map[string]interface{}{
                "npc_id":     npc.ID,
                "context":    gameState,
                "personality": npc.Personality,
            },
        })
    }

    time.Sleep(100 * time.Millisecond)
}
```

---

## API Status & Support

- **Status Page**: https://status.swarm.dev
- **Documentation**: https://docs.swarm.dev
- **Support**: support@swarm.dev
- **Community**: https://community.swarm.dev

---

## Quick Start Checklist

- [ ] Get API key from dashboard
- [ ] Install SDK in your language
- [ ] Create first swarm
- [ ] Submit test task
- [ ] Set up webhook for notifications
- [ ] Explore integration options
- [ ] Join community for best practices

---

**Version**: 1.0.0
**Last Updated**: October 14, 2025
