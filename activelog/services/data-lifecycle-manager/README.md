# Data Lifecycle Manager for SuperInstance Ecosystem

A comprehensive intelligent data management system that maintains the 30GB storage cap while maximizing ML training effectiveness and preserving valuable information for future development.

## Features

### Core Capabilities
- **Intelligent Log and Note Cleanup**: ML-powered cleanup that learns what data is valuable
- **ML Weight Consolidation**: Merges ML model weights when they reach stable states
- **30GB Storage Cap Management**: Intelligent allocation across all 40+ services
- **Self-Learning Garbage Collection**: Bot that learns from deletion success/failure
- **Advanced Summarization**: Condenses information while preserving critical insights
- **Data Value Scoring**: Multi-dimensional scoring (usefulness to bots, humans, ML training)
- **Building Bots Network Integration**: Optimized for the SuperInstance mission

### Machine Learning Components
- **Data Value Neural Network**: Predicts data importance using 15+ features
- **Note Merging Network**: Intelligently combines similar content
- **Garbage Collection Network**: Learns optimal deletion decisions
- **Summarization Quality Network**: Scores and improves summary quality
- **Reinforcement Learning Agent**: Optimizes decisions through experience

### Monitoring & Analytics
- **Real-time Storage Tracking**: Across all services with growth predictions
- **Performance Analytics**: ML training effectiveness and bot improvements
- **Service Integration Health**: Monitors all 40+ services in the ecosystem
- **Predictive Alerts**: Early warning system for storage issues
- **Cross-service Deduplication**: Removes redundant data across services

### Self-Improving Capabilities
- **Continuous Learning**: Models improve based on user and bot feedback
- **Adaptive Strategies**: Automatically adjusts policies based on performance
- **Feedback Loop Processing**: Learns from deletion outcomes and summary quality
- **Performance Optimization**: Continuously optimizes for better results

## Architecture

```
data-lifecycle-manager/
├── main.py                    # Main service orchestrator
├── ml_data_optimizer.py       # ML models and optimization algorithms  
├── analytics_monitor.py       # Comprehensive monitoring system
├── service_integrator.py      # Integration with all ecosystem services
├── self_improving_ml.py       # Self-learning and adaptation system
├── config.json               # Configuration settings
├── requirements.txt          # Python dependencies
├── start.sh                  # Service startup script
└── README.md                 # This file
```

## Quick Start

### 1. Installation
```bash
cd /home/activeloguser/activelog/services/data-lifecycle-manager
./start.sh
```

The startup script will:
- Create a virtual environment
- Install all dependencies
- Set up directory structure
- Initialize databases
- Start the service

### 2. Web Interface
Once started, access the web interface at:
- **Dashboard**: http://localhost:8490/dashboard
- **API Status**: http://localhost:8490/health
- **Storage Status**: http://localhost:8490/status

### 3. Manual Operations
```bash
# Check service status
./start.sh status

# View logs
./start.sh logs

# Restart service
./start.sh restart

# Stop service
./start.sh stop
```

## Configuration

### Storage Limits
Edit `config.json` to adjust storage allocations:
```json
{
  "storage_config": {
    "total_limit_gb": 30.0,
    "service_allocations": {
      "dmlog-core": 4.0,
      "ai-insights": 2.5,
      "bot-ecosystem": 3.5,
      "ml-platform": 5.0
    }
  }
}
```

### Cleanup Policies
Customize retention policies by service importance:
```json
{
  "cleanup_policies": {
    "log_retention_days": {
      "critical_services": 30,
      "important_services": 14,
      "standard_services": 7
    }
  }
}
```

### Service Classifications
Define service importance levels:
```json
{
  "service_classifications": {
    "critical_services": ["dmlog-core", "backup-dr"],
    "important_services": ["ai-insights", "bot-ecosystem"],
    "development_services": ["dev-sandbox", "game-dev-mode"]
  }
}
```

## API Endpoints

### Core Operations
- `GET /health` - Service health check
- `GET /status` - Current storage status
- `POST /cleanup` - Run intelligent cleanup
- `POST /consolidate` - Consolidate ML models
- `POST /summarize` - Create data summaries

### Advanced Features
- `GET /analytics` - Comprehensive analytics data
- `GET /predictions` - Storage exhaustion predictions
- `POST /feedback` - Submit feedback for learning
- `GET /learning-status` - View ML learning progress

## Storage Management Strategy

### Data Classification
1. **Critical Data** (Never delete)
   - Main service files
   - Configuration files
   - Recent backups
   - High-value ML models

2. **Important Data** (Conservative cleanup)
   - Recent logs
   - Active databases
   - Training data in use
   - User-created content

3. **Standard Data** (Regular cleanup)
   - Older logs
   - Cache files
   - Intermediate results
   - Temporary files

4. **Disposable Data** (Aggressive cleanup)
   - Very old logs
   - Temporary files
   - Redundant data
   - Failed operations data

### Cleanup Priorities
1. **Phase 1** (Warning threshold - 85%)
   - Clean temporary files
   - Remove old cache
   - Compress large logs

2. **Phase 2** (Critical threshold - 95%)
   - Aggressive log cleanup
   - Remove redundant data
   - Consolidate ML models

3. **Phase 3** (Emergency - 98%)
   - Remove non-essential data
   - Compress everything possible
   - Alert administrators

## Machine Learning Models

### Data Value Network
- **Input**: 15 features including age, size, access patterns, service importance
- **Output**: Value score (0-1) indicating data importance
- **Training**: Continuous learning from user and bot feedback

### Garbage Collection Network
- **Input**: 12 features including file characteristics and context
- **Output**: Deletion confidence score
- **Learning**: Reinforcement learning from deletion outcomes

### Summarization Network
- **Input**: 8 features about content and quality
- **Output**: Quality score for generated summaries
- **Improvement**: Learns from summary effectiveness ratings

### Note Merging Network
- **Input**: 20 features comparing content similarity and context
- **Output**: Merge decision (none, soft, hard merge)
- **Optimization**: Learns optimal merging strategies

## Integration with SuperInstance Ecosystem

### Service Discovery
- Automatically discovers all services in `/home/activeloguser/activelog/services/`
- Identifies service types (Python, Node.js, Java, etc.)
- Monitors resource usage and health status
- Tracks data patterns per service

### Building Bots Network Optimization
- Prioritizes AI and ML services for resource allocation
- Optimizes data flow between bot services
- Identifies cross-bot learning opportunities
- Preserves data valuable for bot development

### Cross-Service Deduplication
- Finds duplicate files across services
- Identifies similar content for merging
- Maintains service-specific copies when needed
- Optimizes storage without breaking dependencies

## Monitoring & Alerting

### Real-Time Metrics
- Storage usage per service
- Growth rates and predictions  
- ML model performance
- Cleanup effectiveness
- System resource utilization

### Predictive Analytics
- Storage exhaustion forecasting
- Service growth trend analysis
- Performance degradation detection
- Optimization opportunity identification

### Alert Types
- **Critical**: Immediate action required (storage >95%)
- **Warning**: Attention needed (storage >85%)
- **Info**: Notable events and trends
- **Success**: Successful optimizations

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check Python version
python3 --version

# Check permissions
ls -la start.sh

# View startup logs
cat startup.log
```

#### High Memory Usage
- Reduce batch size in `ml_config`
- Disable continuous learning temporarily
- Increase monitoring intervals

#### Storage Not Freeing Up
- Check service classifications in config
- Review cleanup policies
- Manually run aggressive cleanup:
```bash
curl -X POST localhost:8490/cleanup -d '{"target_reduction_gb": 5}'
```

#### Models Not Learning
- Ensure feedback is being submitted
- Check learning status endpoint
- Review training data quality

### Performance Tuning

#### For High-Performance Systems
```json
{
  "ml_config": {
    "batch_size": 64,
    "learning_rate": 0.002,
    "epochs": 100
  },
  "monitoring_config": {
    "resource_monitoring_interval_seconds": 30
  }
}
```

#### For Resource-Constrained Systems
```json
{
  "ml_config": {
    "batch_size": 16,
    "learning_rate": 0.0005,
    "epochs": 25
  },
  "monitoring_config": {
    "resource_monitoring_interval_seconds": 120
  }
}
```

## Development

### Adding New Cleanup Strategies
1. Modify `service_integrator.py`
2. Add strategy to `cleanup_strategies` dict
3. Test with development services first

### Extending ML Models
1. Add new model class to `ml_data_optimizer.py`
2. Register in `DataOptimizer.__init__()`
3. Add training loop to learning engine

### Custom Analytics
1. Extend `analytics_monitor.py`
2. Add new metric classes
3. Update dashboard to display metrics

## Security Considerations

- Secure deletion of sensitive files
- Access logging for all operations
- Configuration validation
- Safe handling of file operations
- Backup before major cleanups

## Future Enhancements

- Quantum-ready optimization algorithms
- Advanced cross-domain learning
- Autonomous optimization mode
- Integration with external storage systems
- Advanced encryption for sensitive data

## Support

For issues or questions:
1. Check the logs: `./start.sh logs`
2. Review configuration: `config.json`
3. Check service status: `./start.sh health`
4. View analytics: http://localhost:8490/dashboard