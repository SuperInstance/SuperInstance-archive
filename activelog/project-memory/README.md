# Intelligent Project Memory System

**Version:** 1.0.0  
**Purpose:** Enable efficient codebase understanding with minimal context window usage  
**Target:** AI assistants working with large codebases  

## Architecture Overview

This system implements a hierarchical knowledge graph with smart compression, progressive disclosure, and bot-specific views to maximize understanding while minimizing context consumption.

### Core Components

1. **Knowledge Graph** (`knowledge/`) - Hierarchical concept mapping with semantic compression
2. **Context Optimizer** (`context/`) - Smart dependency tracking and minimal loading
3. **Bot Views** (`views/`) - Capability-specific documentation versions
4. **Dynamic Generator** (`generator/`) - Automated documentation maintenance
5. **Cache System** (`cache/`) - Performance optimization for repeated access

### Key Features

- **Semantic Compression**: 255-char concept lines with ID-based linking
- **Progressive Disclosure**: Start minimal, expand as needed
- **Delta Encoding**: Only explain differences from standard patterns
- **Smart Path Encoding**: Folders/files encode functionality semantically
- **Context Window Optimization**: Load only relevant branches
- **Bot-Specific Views**: Tailored complexity based on bot capabilities

### Usage

```bash
# Initialize system for a codebase
python generator/init_memory.py ~/activelog/

# Query concept by ID
python context/query.py CORE-001

# Get bot-specific view
python views/get_view.py --bot-type=simple --concept=AUTH

# Update memory after code changes
python generator/update_memory.py ~/activelog/services/
```

### Performance Metrics

- **Context Reduction**: Target 80% reduction in token usage
- **Load Time**: <100ms for concept queries
- **Coverage**: 95% of codebase concepts mapped
- **Accuracy**: 90% semantic precision in compression

## Directory Structure

```
project-memory/
├── knowledge/           # Hierarchical knowledge graph
│   ├── index.md        # Main concept index (255-char lines)
│   ├── core/           # Core system concepts
│   ├── auth/           # Authentication concepts
│   ├── services/       # Service-specific concepts
│   └── patterns/       # Architectural patterns
├── context/            # Context window optimization
│   ├── manifest.json   # Dependency tracking
│   ├── optimizer.py    # Context loading logic
│   └── query.py        # Concept query interface
├── views/              # Bot-specific views
│   ├── simple/         # Simple bot explanations
│   ├── advanced/       # Advanced bot explanations
│   └── selector.py     # Automatic view selection
├── generator/          # Dynamic documentation
│   ├── scanner.py      # Code change detection
│   ├── updater.py      # Memory maintenance
│   └── validator.py    # Link verification
└── cache/              # Performance optimization
    ├── concepts.db     # Cached concept data
    └── patterns.json   # Common pattern cache
```