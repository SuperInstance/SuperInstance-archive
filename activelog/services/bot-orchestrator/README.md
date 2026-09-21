# Bot Orchestration System

An intelligent bot orchestration system with Claude Opus 4.1 director integration, providing advanced multi-bot coordination, context management, and knowledge sharing capabilities.

## Features

### 🤖 Claude Director Integration
- **API Interface**: Complete integration with Claude Opus 4.1 API
- **Task Decomposition**: Intelligent breakdown of complex tasks into subtasks
- **Bot Allocation**: Smart allocation of tasks to optimal bots based on capabilities
- **Context Optimization**: Dynamic context summarization and optimization for token efficiency
- **Progress Monitoring**: Real-time task progress tracking and completion monitoring
- **Error Detection & Recovery**: Automatic error detection with intelligent retry mechanisms
- **Dynamic Reallocation**: Automatic task redistribution based on bot performance
- **Token Usage Tracking**: Comprehensive tracking and management of API token usage
- **Rate Limit Management**: Intelligent rate limiting and request throttling

### 🔄 Multi-Bot Coordination
- **Task Queue Management**: Priority-based task queuing with dependency resolution
- **Dependency Resolution**: Automatic handling of task dependencies and prerequisites
- **Parallel Execution Planning**: Optimized parallel task execution strategies
- **Resource Allocation**: Dynamic resource allocation and management
- **Bot Health Monitoring**: Real-time monitoring of bot health and performance
- **Deadlock Prevention**: Proactive deadlock detection and resolution
- **Work Stealing Algorithm**: Load balancing through intelligent work redistribution
- **Load Balancing**: Multiple load balancing strategies (round-robin, capability-based, performance-weighted)
- **Priority Scheduling**: Advanced priority-based task scheduling
- **Result Aggregation**: Intelligent aggregation of multi-bot task results

### 🧠 Context Management
- **Smart Summarization**: AI-powered context summarization for cheaper bots
- **Context Preservation**: Maintains context consistency across bot interactions
- **Knowledge Graph**: Comprehensive system state knowledge representation
- **Incremental Context Building**: Efficient context building and maintenance
- **Relevance Filtering**: Intelligent filtering of relevant context information
- **Memory Optimization**: Advanced memory usage optimization techniques
- **Cross-Bot Information Sharing**: Seamless information sharing between bots
- **Version Control Integration**: Git-based version control for shared knowledge

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Bot Orchestration System                     │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Server (Port 8450)                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐    ┌─────────────────────────────────────┐ │
│  │  Claude Director │    │      Multi-Bot Coordination        │ │
│  │                  │    │                                     │ │
│  │ • Task Decomp.   │    │ • Task Queue Manager               │ │
│  │ • Bot Allocation │    │ • Parallel Executor                │ │
│  │ • Context Opt.   │    │ • Health Monitor                   │ │
│  │ • Progress Mon.  │    │ • Deadlock Detection               │ │
│  │ • Error Recovery │    │ • Work Stealing                    │ │
│  │ • Token Tracking │    │ • Load Balancing                   │ │
│  └──────────────────┘    └─────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │             Context & Knowledge Management                  │ │
│  │                                                             │ │
│  │ • Context Manager     • Knowledge Graph                    │ │
│  │ • Smart Summarization • Entity Extraction                  │ │
│  │ • Relevance Filtering • Relationship Detection             │ │
│  │ • Memory Optimization • Graph Traversal                    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │          Cross-Bot Information Sharing                     │ │
│  │                                                             │ │
│  │ • Information Store   • Version Control Integration        │ │
│  │ • Pattern Detection   • Knowledge Synthesis                │ │
│  │ • Access Control      • Git-based Persistence              │ │
│  │ • Relevance Scoring   • Collaborative Learning             │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

1. **Prerequisites**:
   ```bash
   # Ensure you're in the activelog directory
   cd ~/activelog/services/bot-orchestrator
   
   # Set up Anthropic API key
   export ANTHROPIC_API_KEY="your-api-key-here"
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize Database**:
   ```bash
   # Databases are automatically initialized on first run
   # Optional: Check if SQLite is available
   python -c "import sqlite3; print('SQLite available')"
   ```

## Usage

### Starting the System

```bash
# Start with default settings (localhost:8450)
python main.py

# Start with custom configuration
python main.py --host 0.0.0.0 --port 8450 --workers 4

# Development mode with auto-reload
python main.py --reload --log-level debug
```

### API Endpoints

#### Health & Status
- `GET /health` - System health check
- `GET /metrics` - Comprehensive system metrics

#### Task Management
- `POST /tasks/submit` - Submit a new task
- `POST /tasks/{task_id}/execute` - Execute a specific task
- `GET /tasks/{task_id}/status` - Get task status
- `GET /tasks/queue/status` - Get queue status

#### Bot Management
- `POST /bots/register` - Register a new bot
- `DELETE /bots/{bot_id}` - Unregister a bot
- `GET /bots/{bot_id}/health` - Get bot health
- `GET /bots/health/overview` - System health overview

#### Context Management
- `POST /context/add` - Add context information
- `GET /context/optimized` - Get optimized context for tasks
- `GET /context/stats` - Context management statistics

#### Knowledge Graph
- `POST /knowledge/add` - Add content to knowledge graph
- `GET /knowledge/context` - Get related context from graph
- `GET /knowledge/stats` - Knowledge graph statistics

#### Information Sharing
- `POST /information/share` - Share information between bots
- `GET /information/relevant` - Get relevant shared information
- `POST /information/synthesize` - Synthesize knowledge on topics
- `GET /information/stats` - Information sharing statistics

### Example Usage

#### Submit and Execute a Task
```python
import requests

# Submit a task
response = requests.post("http://localhost:8450/tasks/submit", json={
    "description": "Analyze the latest sales data and generate insights",
    "priority": "HIGH",
    "estimated_tokens": 3000,
    "context": "Focus on Q4 performance trends",
    "tags": ["analytics", "sales", "reporting"]
})
task_id = response.json()["task_id"]

# Execute the task
response = requests.post(f"http://localhost:8450/tasks/{task_id}/execute")
result = response.json()["execution_result"]
```

#### Register a Bot
```python
response = requests.post("http://localhost:8450/bots/register", json={
    "bot_id": "analytics_bot_01",
    "capabilities": {
        "cpu_capacity": 4.0,
        "memory_capacity": 8.0,
        "specializations": ["data_analysis", "visualization"]
    },
    "max_concurrent": 3
})
```

#### Share Information
```python
response = requests.post("http://localhost:8450/information/share", json={
    "info_type": "BEST_PRACTICE",
    "title": "Efficient Data Processing Pattern",
    "content": "When processing large datasets, use chunking with size 10000...",
    "scope": "TEAM_LEVEL",
    "priority": "HIGH",
    "tags": ["data_processing", "performance", "best_practices"]
}, params={"bot_id": "analytics_bot_01"})
```

## Configuration

### Environment Variables
- `ANTHROPIC_API_KEY` - Required: Your Anthropic API key
- `BOT_ORCHESTRATOR_HOST` - Optional: Host to bind to (default: localhost)
- `BOT_ORCHESTRATOR_PORT` - Optional: Port to bind to (default: 8450)
- `BOT_ORCHESTRATOR_LOG_LEVEL` - Optional: Log level (default: info)

### Database Configuration
The system uses SQLite databases stored in the service directory:
- `context_storage.db` - Context management data
- `knowledge_graph.db` - Knowledge graph data
- `shared_information.db` - Shared information data

### Git Integration
If running within a git repository, the system automatically:
- Creates a `shared_knowledge/` directory for persistent knowledge storage
- Commits knowledge changes to version control
- Tracks knowledge evolution over time

## Architecture Details

### Claude Director
The Claude Director is the core orchestration component that:
- Interfaces directly with Claude Opus 4.1 API
- Decomposes complex tasks into manageable subtasks
- Allocates tasks to optimal bots based on capabilities and current load
- Optimizes context to fit within token limits while preserving essential information
- Monitors task progress and handles error recovery
- Manages API rate limits and token usage

### Multi-Bot Coordination
The coordination layer manages multiple bots through:
- **Task Queue Manager**: Handles task queuing with priorities and dependencies
- **Parallel Executor**: Executes tasks in parallel using various strategies
- **Bot Health Monitor**: Continuously monitors bot health and performance
- **Work Stealing Manager**: Rebalances workload across bots for optimal utilization

### Context Management
Advanced context management system featuring:
- **Smart Summarization**: Uses multiple strategies (extractive, abstractive, hierarchical)
- **Relevance Filtering**: Calculates relevance scores based on task requirements
- **Memory Optimization**: Intelligent caching and storage management
- **Context Preservation**: Maintains context consistency across bot interactions

### Knowledge Graph
Dynamic knowledge representation system with:
- **Entity Extraction**: Identifies entities using AI and pattern matching
- **Relationship Detection**: Discovers relationships between entities
- **Graph Traversal**: Finds relevant context through graph exploration
- **Incremental Building**: Continuously builds and updates the knowledge graph

### Information Sharing
Cross-bot information sharing system providing:
- **Access Control**: Role-based access to shared information
- **Pattern Detection**: Identifies patterns in shared information
- **Knowledge Synthesis**: Combines information from multiple sources
- **Version Control**: Git integration for persistent knowledge storage

## Monitoring & Observability

The system provides comprehensive monitoring through:

### Health Monitoring
- Real-time bot health checks
- System resource monitoring
- Performance metrics tracking
- Deadlock detection and resolution

### Metrics Collection
- Task execution metrics
- Token usage tracking
- Bot performance statistics
- Context management efficiency
- Knowledge graph growth
- Information sharing activity

### Logging
- Structured logging with configurable levels
- Component-specific log channels
- Error tracking and alerting
- Performance monitoring

## Development

### Project Structure
```
bot-orchestrator/
├── main.py                 # FastAPI application and main entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── director/              # Claude Director integration
│   ├── __init__.py
│   └── claude_director.py
├── coordination/          # Multi-bot coordination
│   ├── __init__.py
│   ├── task_queue.py
│   ├── parallel_executor.py
│   └── bot_health_monitor.py
├── context/               # Context management
│   ├── __init__.py
│   ├── context_manager.py
│   └── knowledge_graph.py
└── shared/                # Information sharing
    ├── __init__.py
    └── information_sharing.py
```

### Contributing
1. Follow the existing code structure and patterns
2. Add comprehensive error handling
3. Include proper logging
4. Update documentation for new features
5. Test thoroughly with various scenarios

## Security Considerations

- API keys are managed through environment variables
- Access control for shared information
- Input validation on all API endpoints
- Rate limiting protection
- Secure database access patterns

## Performance Optimization

The system is designed for high performance with:
- Asynchronous processing throughout
- Efficient database queries with proper indexing
- Smart caching strategies
- Load balancing across multiple bots
- Memory optimization techniques
- Token usage optimization

## Troubleshooting

### Common Issues
1. **API Key Issues**: Ensure `ANTHROPIC_API_KEY` is set correctly
2. **Port Conflicts**: Check if port 8450 is already in use
3. **Database Errors**: Ensure write permissions in the service directory
4. **Memory Issues**: Monitor system resources and adjust bot limits

### Logging
Check logs at:
- Console output for real-time monitoring
- `/home/activeloguser/activelog/logs/bot-orchestrator.log` for persistent logs

### Health Checks
Use the `/health` endpoint to verify system status:
```bash
curl http://localhost:8450/health
```

## License

This project is part of the ActiveLog ecosystem and follows the same licensing terms.