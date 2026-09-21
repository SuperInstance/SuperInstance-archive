# SuperInstance Smart Task System 🧠

Intelligent task classification system that automatically selects the optimal Claude model for each task, maximizing token efficiency and minimizing costs while maintaining quality.

## 🎯 Key Features

### **Automatic Model Selection**
- **Haiku**: Simple tasks, file operations, basic fixes (up to 90% cost savings)
- **Sonnet**: Standard development work, API design, refactoring (balanced cost/performance)  
- **Opus**: Complex reasoning, architecture, novel solutions (premium capabilities)

### **Intelligence Classification**
- Analyzes task complexity, reasoning requirements, creativity needs
- Estimates token usage and costs before execution
- Provides confidence scores and reasoning for model selection
- Tracks performance and optimizes over time

### **Token Efficiency**
- Reduces API costs by up to 95% through intelligent model selection
- Optimizes prompts based on model capabilities  
- Batch processing for similar complexity tasks
- Real-time cost tracking and optimization

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Task Input    │───▶│ Task Classifier  │───▶│  Model Router   │
│ (Description,   │    │ (Complexity      │    │  (Haiku/Sonnet/ │
│  Context, etc.) │    │  Analysis)       │    │   Opus)         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                           │
                              ▼                           ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Cost Optimizer   │    │  Claude API     │
                       │ (Token Est.,     │    │  (Execution)    │
                       │  Batch Proc.)    │    │                 │
                       └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 1. Installation
```bash
cd /home/activeloguser/activelog/services/smart-task-system
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-api-key"
```

### 2. Start the Smart Task API
```bash
python task_api.py --port 8470
```

### 3. Submit Tasks via API
```bash
# Simple task - automatically routes to Haiku
curl -X POST http://localhost:8470/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Fix typo in config file",
    "priority": "LOW"
  }'

# Complex task - automatically routes to Opus
curl -X POST http://localhost:8470/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Design scalable microservices architecture for real-time analytics",
    "context": "Handle millions of data points with advanced correlation analysis", 
    "priority": "CRITICAL"
  }'
```

## 📊 Task Intelligence Examples

### **Automatic Classification Results:**

```python
# TRIVIAL → Haiku (95% cost savings)
"Fix typo in README.md"
# Model: haiku, Cost: $0.0012, Confidence: 95%

# MODERATE → Sonnet (balanced)
"Implement user authentication API with JWT tokens"  
# Model: sonnet, Cost: $0.045, Confidence: 87%

# EXPERT → Opus (premium reasoning)
"Research novel ML approach for personalized recommendations"
# Model: opus, Cost: $0.234, Confidence: 92%
```

## 🔧 Integration Points

### **For Bots Leaving Tasks:**

#### 1. **Direct API Submission (Recommended)**
```python
import aiohttp

async def submit_smart_task(description, context="", priority="MEDIUM"):
    async with aiohttp.ClientSession() as session:
        async with session.post("http://localhost:8470/tasks/submit", json={
            "description": description,
            "context": context, 
            "priority": priority,
            "user_id": "my-bot-id"
        }) as response:
            return await response.json()

# Example usage
result = await submit_smart_task(
    "Optimize database queries for fitness API",
    "Need sub-100ms response times for user experience",
    "HIGH"
)
print(f"Task routed to: {result['analysis']['recommended_model']}")
print(f"Estimated cost: ${result['analysis']['estimated_cost']:.4f}")
```

#### 2. **Micro Updates Log Integration** 
```bash
# Smart system monitors this log automatically
echo "$(date +%H:%M)|my-bot|ASSIGN|optimize-redis-caching-layer" >> /home/activeloguser/activelog/micro_updates.log
```

#### 3. **Task File Drops**
```bash
# Add to monitored task files
echo "- HIGH: Implement user dashboard components with React" >> /home/activeloguser/activelog/task_assignments_optimized.txt
```

#### 4. **Batch Processing**
```python
# Submit multiple tasks for optimized distribution
tasks = [
    {"description": "Fix authentication bug", "priority": "URGENT"},
    {"description": "Update API documentation", "priority": "LOW"}, 
    {"description": "Design caching architecture", "priority": "HIGH"}
]

result = await session.post("http://localhost:8470/tasks/batch", json={
    "tasks": tasks,
    "optimize_distribution": True
})
```

### **For Automatic Bot Processing:**

The system automatically:
1. **Monitors** micro_updates.log for new ASSIGN/URGENT tasks
2. **Analyzes** task complexity and requirements  
3. **Routes** to optimal Claude model
4. **Executes** with model-specific prompts
5. **Logs** results back to micro_updates.log

## 💡 Smart Model Selection Logic

### **Decision Factors:**

**Task Complexity Analysis:**
- Pattern matching against known complexity indicators
- Keywords: "simple", "complex", "architecture", "research", etc.
- File analysis: number and types of files involved

**Reasoning Requirements:**
- Advanced logic needs: design, analyze, solve, optimize
- Creative requirements: innovative, novel, user experience
- Time sensitivity: urgent/critical tasks

**Cost Optimization:**
- Token estimation based on task scope
- Batch processing for similar tasks  
- Downgrade model if task is simpler than initially assessed
- Upgrade model if quality/reasoning is critical

### **Example Classifications:**

```
TRIVIAL (Haiku - $0.001):
✓ "Read config file and list settings"
✓ "Fix indentation in Python script"  
✓ "Add comment to function"

SIMPLE (Haiku - $0.005):
✓ "Basic debugging of syntax error"
✓ "Update configuration value"
✓ "Add logging statement"

MODERATE (Sonnet - $0.025):  
✓ "Implement REST API endpoint"
✓ "Refactor database queries"
✓ "Create unit tests"

COMPLEX (Sonnet/Opus - $0.100):
✓ "Design authentication system"
✓ "Optimize performance bottleneck"  
✓ "Implement caching strategy"

EXPERT (Opus - $0.300):
✓ "Architecture for scalable system"
✓ "Research novel algorithms"
✓ "Cross-domain integration design"
```

## 📈 Cost Savings Analysis

### **Typical Cost Reductions:**

| Task Type | Without Smart Routing | With Smart Routing | Savings |
|-----------|---------------------|-------------------|---------|
| Simple fixes | $0.15 (Opus) | $0.003 (Haiku) | **98%** |
| Documentation | $0.12 (Opus) | $0.008 (Haiku) | **93%** |
| Standard dev | $0.18 (Opus) | $0.035 (Sonnet) | **81%** |
| Architecture | $0.25 (Opus) | $0.25 (Opus) | 0% (optimal) |

**Average Savings: 75-85%** across mixed workloads

### **Real-time Cost Tracking:**
```bash
# Get performance report
curl http://localhost:8470/performance/report

{
  "performance_summary": {
    "total_tasks_processed": 1247,
    "total_cost": 45.67,
    "average_cost_per_task": 0.0366
  },
  "model_performance": {
    "haiku": {"tasks_completed": 623, "average_cost_per_task": 0.0045},
    "sonnet": {"tasks_completed": 498, "average_cost_per_task": 0.0287},  
    "opus": {"tasks_completed": 126, "average_cost_per_task": 0.2156}
  }
}
```

## 🎛️ API Endpoints

### **Core Task Management:**
- `POST /tasks/submit` - Submit single task
- `POST /tasks/batch` - Submit multiple tasks  
- `GET /tasks/query` - Query tasks with filters
- `GET /tasks/{task_id}` - Get task details

### **Intelligence & Analysis:**
- `POST /tasks/analyze` - Analyze without execution
- `GET /models/capabilities` - Model information
- `GET /performance/report` - Cost & performance analytics
- `GET /queue/status` - Queue statistics

### **Advanced Features:**
- `POST /tasks/force-model` - Override model selection
- `GET /tasks/optimal/{model}` - Get tasks suited for model
- `WebSocket /ws/task-updates` - Real-time updates

## 🔍 Monitoring & Debugging

### **Real-time Queue Status:**
```bash
curl http://localhost:8470/queue/status

{
  "queue_summary": {
    "total_pending_tasks": 23,
    "model_distribution": {
      "haiku": 12, "sonnet": 8, "opus": 3
    },
    "total_estimated_cost": 3.45
  }
}
```

### **Task Analysis:**
```bash
curl -X POST http://localhost:8470/tasks/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Implement Redis caching for API endpoints",
    "context": "Need to reduce database load",
    "priority": "HIGH"
  }'

{
  "analysis": {
    "complexity": "moderate",
    "recommended_model": "sonnet", 
    "confidence": 0.87,
    "reasoning": "Standard development task with caching implementation - Sonnet balanced choice",
    "estimated_cost": 0.0423,
    "requires_reasoning": true,
    "requires_creativity": false
  },
  "model_comparison": {
    "haiku": {"estimated_cost": 0.0089, "recommended": false},
    "sonnet": {"estimated_cost": 0.0423, "recommended": true},
    "opus": {"estimated_cost": 0.1847, "recommended": false}
  }
}
```

## ⚡ Performance Optimization

### **Batch Processing:**
```python
# Automatically groups similar tasks by model
tasks = [
    {"description": "Fix bug in auth.py", "priority": "HIGH"},
    {"description": "Update README", "priority": "LOW"},
    {"description": "Design user interface", "priority": "MEDIUM"}
]

# System optimally distributes:
# Haiku batch: README update
# Sonnet batch: bug fix, UI design  
# Results in 40% faster processing + cost savings
```

### **Adaptive Learning:**
- Tracks model performance over time
- Adjusts classification based on success rates
- Optimizes token estimates from actual usage
- Learns project-specific patterns

### **Token Efficiency:**
- Model-specific prompt optimization
- Context trimming for large inputs
- Smart batching of similar complexity tasks
- Real-time cost monitoring and alerts

## 🔒 Integration Security

### **API Security:**
- Rate limiting on task submission
- Input validation and sanitization  
- Cost limits per user/bot
- Audit logging for all operations

### **Model Access Control:**
- Configurable model access by user
- Cost budgets per bot/user
- Priority-based resource allocation
- Emergency cost circuit breakers

## 🎯 Use Cases

### **Perfect for Haiku (90%+ cost savings):**
- File operations, config updates
- Simple bug fixes, typos
- Basic documentation updates  
- Formatting and validation

### **Ideal for Sonnet (50-80% savings vs Opus):**
- API development and integration
- Database optimization
- Code refactoring and testing
- Standard development tasks

### **Requires Opus (optimal quality):**
- System architecture design
- Complex algorithm development  
- Research and analysis tasks
- Novel problem solving

The Smart Task System ensures every task gets the right level of intelligence at the optimal cost, making your SuperInstance development both efficient and economical! 🚀