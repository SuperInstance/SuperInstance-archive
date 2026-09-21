# Quick Start Guide

## Overview

This guide will help you get the Unified Agent Backend running locally in 10 minutes.

## Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Git

## 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd unified-agent-backend

# Copy environment configuration
cp .env.example .env

# Edit .env with your API keys
nano .env
```

## 2. Start Services

```bash
# Start all services with Docker Compose
docker-compose up -d

# This starts:
# - PostgreSQL (database)
# - Redis (cache + streams)
# - Qdrant (vector database)
# - API Server
# - Web UI
```

## 3. Verify Installation

```bash
# Check service status
docker-compose ps

# View API documentation
open http://localhost:8000/docs

# Check health
curl http://localhost:8000/health
```

## 4. Create Your First Agent

```bash
# Using the API
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Research Assistant",
    "role": "researcher",
    "system_prompt": "You are a helpful research assistant.",
    "capabilities": ["search", "summarize"],
    "model_config": {
      "provider": "openai",
      "model": "gpt-3.5-turbo"
    }
  }'
```

## 5. Create a Simple Workflow

```python
# workflow_example.py
import asyncio
import httpx

async def create_workflow():
    workflow = {
        "name": "Research Workflow",
        "description": "Search and summarize a topic",
        "definition": {
            "nodes": [
                {
                    "id": "search",
                    "type": "agent_task",
                    "agent_id": "research-assistant",
                    "task": {
                        "type": "search",
                        "input": {"query": "AI agent frameworks"}
                    }
                },
                {
                    "id": "summarize",
                    "type": "agent_task",
                    "agent_id": "research-assistant",
                    "task": {
                        "type": "summarize",
                        "input": {"max_length": 100}
                    }
                }
            ],
            "edges": [
                {"from": "search", "to": "summarize"}
            ]
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/workflows",
            json=workflow
        )
        return response.json()

# Run the workflow
result = asyncio.run(create_workflow())
print(f"Created workflow: {result['id']}")
```

## 6. Execute the Workflow

```bash
# Execute via API
curl -X POST http://localhost:8000/api/v1/workflows/{workflow-id}/execute \
  -H "Content-Type: application/json" \
  -d '{}'

# Monitor execution
curl http://localhost:8000/api/v1/executions/{execution-id}
```

## 7. Use WebSocket for Real-time Updates

```javascript
// client.js
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('Update:', message);

    if (message.type === 'complete') {
        console.log('Workflow completed:', message.data);
    }
};

// Subscribe to execution updates
ws.send(JSON.stringify({
    type: 'subscribe',
    executionId: 'your-execution-id'
}));
```

## Development Mode

### Local Python Development

```bash
# Install dependencies
pip install poetry
poetry install

# Activate virtual environment
poetry shell

# Run tests
pytest

# Start API server in development
uvicorn src.main:app --reload --port 8000

# Start worker processes
python -m src.worker
```

### Code Structure

```
unified-agent-backend/
├── src/
│   ├── agents/          # Agent implementations
│   ├── workflows/       # Workflow engine
│   ├── memory/          # Memory systems
│   ├── tools/           # Tool management
│   ├── api/             # FastAPI routes
│   └── models/          # Data models
├── tests/               # Test suite
├── docker/              # Docker configs
├── docs/                # Documentation
├── scripts/             # Utility scripts
└── docker-compose.yml   # Development stack
```

## Next Steps

1. **Explore Examples**: Check `/examples` directory for more workflows
2. **Read Documentation**: Full docs at `/docs`
3. **Configure Models**: Add your LLM provider keys to `.env`
4. **Build Custom Tools**: Create your own tools in `/src/tools`
5. **Deploy**: Follow deployment guide for production setup

## Common Issues

### Port Already in Use
```bash
# Kill existing process
sudo lsof -i :8000
kill -9 <PID>

# Or use different port
docker-compose -f docker-compose.yml -f docker-compose.alt.yml up
```

### Memory Issues
```bash
# Increase Docker memory limits
docker system prune -a

# Or reduce memory usage in .env
MEMORY_LIMIT=512m
```

### API Key Issues
```bash
# Verify API keys are set
cat .env | grep -E "(OPENAI|ANTHROPIC)_KEY"

# Test API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://api.openai.com/v1/models
```

## Need Help?

- Check troubleshooting guide: `/docs/TROUBLESHOOTING.md`
- View API docs: http://localhost:8000/docs
- Review examples: `/examples/`
- Open an issue on GitHub

## Performance Tips

1. **Use Local Models**: Configure Ollama for free local inference
2. **Enable Caching**: Set Redis cache for faster responses
3. **Batch Requests**: Use bulk operations for multiple tasks
4. **Monitor Resources**: Check `/metrics` endpoint for usage stats

## Security Notes

- Change default passwords in production
- Use HTTPS in production (configure in nginx.conf)
- Enable authentication (set AUTH_REQUIRED=true)
- Review security guide: `/docs/SECURITY.md`

Happy building! 🚀