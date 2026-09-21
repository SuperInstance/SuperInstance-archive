# Smart Path Encoding Guide

**Purpose:** Encode maximum semantic meaning in file paths and names  
**Goal:** Reading a path should instantly communicate purpose and context  

## Core Principles

1. **Hierarchical Semantics**: Each path level adds semantic meaning
2. **Maximum Density**: Every character serves a purpose
3. **Predictable Structure**: Consistent patterns across the system
4. **Self-Documenting**: Paths tell the complete story

## Path Structure Template

```
~/activelog/project-memory/{domain}/{capability}/{specificity}/{implementation}.{format}
```

### Examples

```
~/activelog/project-memory/
├── knowledge/auth/jwt/token-validation-middleware.md
├── knowledge/services/api-gateway/request-routing-logic.md  
├── knowledge/patterns/fastapi/service-template-structure.md
├── context/optimization/token-budget/progressive-loading.md
├── views/bot-types/simple/concept-summaries.md
├── cache/performance/query-results/concept-lookups.db
```

## Domain Categories

### knowledge/ - Concept Documentation
```
knowledge/{concept-category}/{sub-domain}/{specific-topic}.md

Examples:
- knowledge/auth/jwt/token-expiry-handling.md
- knowledge/services/database/connection-pooling.md  
- knowledge/frontend/react/component-patterns.md
- knowledge/patterns/architecture/microservice-communication.md
```

### context/ - Context Management
```
context/{optimization-type}/{strategy}/{implementation}.{ext}

Examples:
- context/token-budget/progressive-disclosure/view-selector.py
- context/dependency-resolution/graph-traversal/loader.py
- context/caching/query-optimization/result-cache.json
```

### views/ - Bot-Specific Views  
```
views/{bot-capability}/{view-type}/{concept-category}/

Examples:
- views/simple/summaries/services/
- views/advanced/explanations/auth/
- views/expert/deep-dive/architecture/
```

### cache/ - Performance Optimization
```
cache/{cache-type}/{data-category}/{specific-cache}.{ext}

Examples:
- cache/concepts/frequently-accessed/high-priority.db
- cache/patterns/code-analysis/service-templates.json
- cache/performance/query-times/optimization-stats.json
```

## File Naming Conventions

### Semantic Suffixes
- **-pattern.md**: Architectural or code patterns
- **-guide.md**: How-to documentation  
- **-reference.md**: API or technical reference
- **-overview.md**: High-level system overview
- **-implementation.md**: Implementation details
- **-optimization.md**: Performance optimization info

### Action-Based Names
- **validate-**: Validation logic (validate-jwt-token.md)
- **process-**: Processing workflows (process-user-request.md) 
- **manage-**: Management operations (manage-session-lifecycle.md)
- **optimize-**: Optimization strategies (optimize-query-performance.md)
- **analyze-**: Analysis procedures (analyze-code-complexity.md)

### Component-Based Names
- **{component}-{action}-{object}**: auth-validate-token.md
- **{system}-{subsystem}-{feature}**: api-gateway-rate-limiting.md
- **{domain}-{capability}-{implementation}**: frontend-state-management.md

## Hierarchical Encoding Examples

### Authentication System
```
knowledge/auth/
├── overview/
│   ├── auth-architecture-overview.md
│   └── security-model-explanation.md
├── jwt/
│   ├── token-generation-process.md
│   ├── token-validation-middleware.md
│   └── token-refresh-strategy.md
├── 2fa/
│   ├── totp-implementation-guide.md
│   └── backup-codes-management.md
└── integration/
    ├── service-middleware-setup.md
    └── frontend-auth-flow.md
```

### Service Architecture
```
knowledge/services/
├── patterns/
│   ├── fastapi-service-template.md
│   ├── database-connection-pattern.md
│   └── health-check-implementation.md
├── api-gateway/
│   ├── request-routing-logic.md
│   ├── load-balancing-strategy.md
│   └── authentication-proxy.md
├── data-flow/
│   ├── inter-service-communication.md
│   ├── event-driven-patterns.md
│   └── data-synchronization.md
└── deployment/
    ├── containerization-strategy.md
    ├── service-discovery.md
    └── monitoring-integration.md
```

### Context Optimization
```
context/
├── token-budget/
│   ├── progressive-loading/
│   │   ├── dependency-resolver.py
│   │   └── context-expander.py
│   ├── compression/
│   │   ├── semantic-aliases.json
│   │   └── delta-encoding.py
│   └── prioritization/
│       ├── concept-scorer.py
│       └── relevance-ranker.py
├── caching/
│   ├── query-optimization/
│   │   ├── result-cache.py
│   │   └── invalidation-strategy.py
│   └── pattern-recognition/
│       ├── common-queries.json
│       └── usage-analytics.py
└── bot-adaptation/
    ├── capability-detection/
    │   ├── analyze-bot-description.py
    │   └── context-complexity-scorer.py
    └── view-selection/
        ├── optimal-detail-level.py
        └── progressive-disclosure.py
```

## Semantic Density Optimization

### Path Compression Techniques

1. **Abbreviations**: Use when clear (auth vs authentication)
2. **Hyphenation**: Connect related concepts (jwt-token-validation)
3. **Omit Redundancy**: Don't repeat parent directory info
4. **Action-First**: Lead with action verbs when appropriate

### Examples of High Semantic Density

```
❌ Low Density:
knowledge/authentication/json-web-tokens/how-to-validate-tokens.md

✅ High Density:  
knowledge/auth/jwt/validate-tokens.md

❌ Low Density:
context/optimization/for-token-budget/progressive-loading-implementation.py

✅ High Density:
context/token-budget/progressive-loading/implementation.py
```

## Directory Structure Patterns

### Functional Hierarchy (Recommended)
```
{domain}/{function}/{implementation}/
Example: knowledge/auth/jwt/
```

### Layer-Based Organization
```
{domain}/{layer}/{component}/
Example: knowledge/services/data-layer/
```

### Feature-Based Grouping
```
{domain}/{feature}/{aspect}/
Example: knowledge/bot-ecosystem/routing/
```

## Path Encoding Benefits

### For AI Assistants
1. **Instant Context**: Path provides immediate understanding
2. **Predictable Discovery**: Can guess paths for related content
3. **Hierarchical Learning**: Can traverse from general to specific
4. **Semantic Relationships**: Related paths indicate related concepts

### For Developers
1. **Self-Documenting**: No need to open files to understand purpose
2. **Consistent Organization**: Predictable structure across domains
3. **Easy Navigation**: Logical path progression
4. **Maintenance**: Clear ownership and responsibility

### For System Performance
1. **Efficient Caching**: Path-based cache keys
2. **Lazy Loading**: Load only needed path branches
3. **Predictive Prefetching**: Anticipate related path needs
4. **Compression**: Path patterns enable compression

## Usage Guidelines

### Do's ✅
- Use consistent verb forms (validate, process, manage)
- Group related concepts in same directory
- Use hyphens for multi-word concepts
- Keep directory depth reasonable (3-5 levels)
- Make every path component meaningful

### Don'ts ❌
- Don't use generic names (utils, helpers, misc)
- Don't create deep nesting without purpose
- Don't abbreviate unless universally clear
- Don't mix naming conventions in same hierarchy
- Don't create single-item directories unnecessarily

## Implementation Examples

### Bot Capability Detection
```python
# Path: context/bot-adaptation/capability-detection/analyze-description.py

def detect_capability_from_path(file_path: str) -> BotCapability:
    """Detect optimal bot capability from semantic path."""
    if "expert" in file_path or "optimization" in file_path:
        return BotCapability.EXPERT
    elif "advanced" in file_path or "implementation" in file_path:
        return BotCapability.ADVANCED
    elif "simple" in file_path or "overview" in file_path:
        return BotCapability.BASIC
    return BotCapability.INTERMEDIATE
```

### Content Loading
```python  
# Path: context/optimization/progressive-loading/path-aware-loader.py

def load_by_semantic_path(base_path: str, depth: int = 2) -> Dict:
    """Load content using semantic path traversal."""
    content = {}
    
    # Load overview first (semantic priority)
    overview_paths = glob.glob(f"{base_path}/**/overview/*.md")
    for path in overview_paths:
        content[extract_concept_from_path(path)] = load_optimized(path)
    
    # Load implementation details if budget allows
    if depth > 1:
        impl_paths = glob.glob(f"{base_path}/**/implementation/*.md")
        for path in impl_paths:
            if within_token_budget():
                content[extract_concept_from_path(path)] = load_optimized(path)
    
    return content
```

This path encoding system enables maximum semantic density while maintaining human readability and AI assistant efficiency.