# Project Memory Usage Examples

**System:** Intelligent Project Memory for AI Assistants  
**Goal:** Maximize codebase understanding with minimal context window usage  

## Quick Start

### 1. Initialize System for Existing Project
```bash
# Analyze what would be generated (dry run)
./pmem.py init ~/activelog --dry-run

# Initialize complete system  
./pmem.py init ~/activelog

# Check system health
./pmem.py stats
```

### 2. Query Individual Concepts
```bash
# Get advanced view of core architecture
./pmem.py query CORE-001

# Get simple view optimized for basic bots
./pmem.py query AUTH-001 --bot-type=simple --max-tokens=500

# Query without loading dependencies (faster)
./pmem.py query SVC-001 --no-deps
```

### 3. Get Optimized Views for Specific Bots
```bash
# For a simple code assistant
./pmem.py view "Basic code helper bot" "How do I add authentication?" "CORE-001,AUTH-001"

# For advanced system designer
./pmem.py view "Expert system architect with ML knowledge" "Optimize the routing system" "AI-001,PERF-001,SCALE-001"

# For debugging assistant  
./pmem.py view "Debug specialist bot" "Fix memory leak in auth service" "AUTH-001,MON-001,DEBUG-001"
```

## Advanced Usage Scenarios

### Bot Integration Examples

#### 1. Simple Task Bot (50-200 tokens budget)
```python
from context.optimizer import ContextOptimizer, ConceptQuery, BotType

optimizer = ContextOptimizer()
query = ConceptQuery(
    concept_id="CORE-001",
    bot_type=BotType.SIMPLE,
    max_tokens=200,
    include_dependencies=False,
    expand_level=ViewLevel.SIMPLE
)

response = optimizer.query_concept(query)
print(f"Token-optimized content ({response.token_count} tokens):")
print(response.content)
```

#### 2. Advanced Development Assistant (2000-4000 tokens)
```python
from views.selector import ViewSelector

selector = ViewSelector()
package = selector.create_bot_specific_documentation(
    concept_ids=["CORE-001", "AUTH-001", "SVC-001"], 
    bot_description="Advanced Python developer with FastAPI experience",
    user_query="Help me add a new microservice with authentication"
)

print(f"Optimized for {package['bot_capability']} bot:")
print(f"Selected concepts: {package['selected_concepts']}")
print(f"Token budget: {package['token_budget']}")
```

#### 3. Expert System Architect (4000+ tokens)
```python
# Load comprehensive context for complex architectural decisions
concepts = ["CORE-001", "AUTH-001", "SVC-001", "API-001", "SCALE-001", "PERF-001"]

for concept_id in concepts:
    query = ConceptQuery(
        concept_id=concept_id,
        bot_type=BotType.EXPERT,
        max_tokens=8000 // len(concepts),  # Distribute budget
        include_dependencies=True,
        expand_level=ViewLevel.FULL
    )
    response = optimizer.query_concept(query)
    # Process full architectural context...
```

## Continuous Documentation Maintenance

### 1. Monitor Code Changes
```bash
# Scan for changes since last run
./pmem.py scan

# Get detailed change impact (JSON output)
./pmem.py scan --json | jq '.impact_summary'
```

### 2. Update Documentation Automatically
```bash
# Preview update tasks
./pmem.py update

# Execute high-priority updates automatically
./pmem.py update --auto-approve

# Verbose output with error details
./pmem.py update --auto-approve --verbose
```

### 3. Automated Workflows
```bash
#!/bin/bash
# daily-memory-maintenance.sh

echo "🔍 Scanning for code changes..."
./pmem.py scan --json > /tmp/scan_results.json

# Check if updates needed
CHANGES=$(jq '.changes_found' /tmp/scan_results.json)

if [ "$CHANGES" -gt 0 ]; then
    echo "📝 Found $CHANGES changes, updating documentation..."
    ./pmem.py update --auto-approve
    
    echo "📊 System health check..."
    ./pmem.py stats
fi

echo "✅ Daily maintenance complete"
```

## Context Window Optimization Examples

### 1. Progressive Disclosure Pattern
```python
# Start with minimal context
initial_concepts = ["CORE-001"]  # Just architecture overview
detailed_concepts = []

# Expand based on user questions
user_asks_about_auth = True
if user_asks_about_auth:
    detailed_concepts.append("AUTH-001")

user_asks_about_performance = True  
if user_asks_about_performance:
    detailed_concepts.append("PERF-001", "MON-001")

# Load optimized context
total_budget = 2000
for concept_id in initial_concepts + detailed_concepts:
    query = ConceptQuery(
        concept_id=concept_id,
        max_tokens=total_budget // len(initial_concepts + detailed_concepts),
        expand_level=ViewLevel.ADVANCED
    )
    # Load and process...
```

### 2. Semantic Compression
```python
# Use aliases for common patterns
aliases = {
    "STD-AUTH": "AUTH-001",  # Standard authentication flow
    "SVC-TEMPLATE": "SVC-001",  # FastAPI service template  
    "FE-REACT": "FE-001"  # React frontend pattern
}

# Reference compressed concepts
compressed_context = "User wants to add STD-AUTH to new service following SVC-TEMPLATE"
# Expands to full concepts only when needed
```

### 3. Delta Encoding for Variations
```python
# Base pattern (loaded once)
base_service = load_concept("SVC-001")  # FastAPI service template

# Service variations (only differences)
auth_service_delta = {
    "additional_dependencies": ["python-jose", "passlib"],
    "additional_endpoints": ["/login", "/logout", "/refresh"],
    "additional_middleware": ["JWT validation", "Rate limiting"]
}

# Reconstruct full understanding with minimal tokens
full_auth_service = merge_with_base(base_service, auth_service_delta)
```

## Integration with Development Workflows  

### 1. Pre-commit Hook Integration
```bash
# .git/hooks/pre-commit
#!/bin/bash
echo "🧠 Updating project memory..."

# Quick scan and update
cd project-memory
./pmem.py scan --json | jq -r '.concepts_affected' | grep -q "0" || {
    echo "📝 Code changes detected, updating memory..."
    ./pmem.py update --auto-approve
}
```

### 2. CI/CD Pipeline Integration
```yaml
# .github/workflows/documentation.yml
name: Maintain Project Memory

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  update-memory:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Update Project Memory
        run: |
          cd project-memory
          ./pmem.py scan
          ./pmem.py update --auto-approve
          
      - name: Commit Memory Updates
        run: |
          git config user.name "Project Memory Bot"
          git add project-memory/
          git commit -m "🧠 Update project memory" || exit 0
          git push
```

### 3. IDE Plugin Integration
```python
# VSCode extension integration example
def get_contextual_help(cursor_position, max_tokens=1000):
    """Get contextual help based on cursor position."""
    
    # Analyze current file and position
    current_file = get_current_file()
    concepts = identify_concepts_from_file(current_file)
    
    # Get optimized context
    cli = ProjectMemoryCLI()
    result = cli.get_smart_view(
        concepts,
        "VSCode development assistant",
        f"Help with code at {current_file}:{cursor_position}"
    )
    
    return result['content']
```

## Performance Optimization Examples

### 1. Caching Strategies
```python
# Query result caching
from functools import lru_cache

@lru_cache(maxsize=128)
def get_cached_concept(concept_id: str, bot_type: str) -> str:
    """Cache frequently accessed concepts."""
    query = ConceptQuery(concept_id=concept_id, bot_type=BotType(bot_type))
    response = optimizer.query_concept(query)
    return response.content

# Pattern recognition caching
common_patterns = {
    "new_service": ["CORE-001", "SVC-001", "AUTH-001"],
    "frontend_development": ["FE-001", "API-001", "UI-001"],  
    "debugging_auth": ["AUTH-001", "DEBUG-001", "LOG-001"]
}
```

### 2. Lazy Loading Implementation
```python
class LazyConceptLoader:
    """Load concepts only when accessed."""
    
    def __init__(self, concept_ids: List[str]):
        self.concept_ids = concept_ids
        self._loaded_concepts = {}
        
    def __getitem__(self, concept_id: str) -> str:
        if concept_id not in self._loaded_concepts:
            self._loaded_concepts[concept_id] = self._load_concept(concept_id)
        return self._loaded_concepts[concept_id]
    
    def _load_concept(self, concept_id: str) -> str:
        # Load with minimal context first
        query = ConceptQuery(concept_id=concept_id, expand_level=ViewLevel.SIMPLE)
        return optimizer.query_concept(query).content
```

### 3. Batch Loading Optimization
```python
def load_concept_batch(concept_ids: List[str], total_budget: int) -> Dict[str, str]:
    """Load multiple concepts within total token budget."""
    
    # Optimize budget distribution
    optimized_queries = optimizer.optimize_query_list(concept_ids, total_budget)
    
    results = {}
    for query in optimized_queries:
        response = optimizer.query_concept(query)
        results[query.concept_id] = response.content
        
    return results
```

## Monitoring and Analytics

### 1. Usage Tracking
```bash
# Get system usage statistics
./pmem.py stats --json | jq '.recent_activity'

# Monitor token usage efficiency  
./pmem.py stats | grep -E "(utilization|compression)"
```

### 2. Performance Metrics
```python
# Track query performance
import time

def measure_query_performance(concept_id: str):
    start_time = time.time()
    
    query = ConceptQuery(concept_id=concept_id)
    response = optimizer.query_concept(query)
    
    end_time = time.time()
    
    return {
        "concept_id": concept_id,
        "query_time_ms": (end_time - start_time) * 1000,
        "token_count": response.token_count,
        "compression_ratio": response.compression_ratio,
        "cache_hit": check_cache_hit(concept_id)
    }
```

### 3. Quality Assessment
```python
def assess_context_quality(loaded_concepts: Dict[str, str], user_task: str) -> float:
    """Assess how well loaded context matches user needs."""
    
    # Analyze task requirements
    task_keywords = extract_keywords(user_task)
    concept_coverage = calculate_coverage(loaded_concepts, task_keywords)
    
    # Calculate quality score
    return concept_coverage * token_efficiency * relevance_score
```

This system provides maximum flexibility while ensuring optimal performance for different bot types and use cases.