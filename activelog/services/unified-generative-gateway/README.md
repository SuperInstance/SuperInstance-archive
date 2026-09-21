# Building Bots Network - Unified Generative Gateway

## Overview

The **Building Bots Network Unified Generative Gateway** serves as the central nervous system for orchestrating all specialized construction bots in the network. This gateway embodies the network's mission of delivering construction excellence through intelligent coordination of AI-powered building services.

## Architecture

### Core Components

1. **Unified Generative Gateway** (`main.py`)
   - Central orchestration engine
   - Intelligent routing and load balancing
   - Multi-modal generation workflows
   - Quality assurance across all outputs

2. **Real-time Dashboard** (`dashboard.py`)
   - Live network monitoring
   - Performance visualization
   - Resource utilization tracking
   - Interactive control interface

3. **Service Orchestrator** (`orchestrator.py`)
   - Automatic service startup/shutdown
   - Health monitoring and failover
   - Performance tracking
   - Network coordination

## Building Bots Network Services

The gateway orchestrates the following specialized construction bots:

### Core Generation Services
- **Generative Tools Hub** (Port 8500) - Multi-modal generation suite
- **Image Generation Service** (Port 8480) - Visual construction specialist
- **Audio Generation Service** (Port 8481) - Audio construction specialist  
- **Video Generation Service** (Port 8483) - Video construction specialist
- **Code Generation Service** (Port 8482) - Code construction specialist

### Intelligence & Coordination Services
- **AI Picker System** (Port 8470) - Intelligence optimization
- **Data Lifecycle Manager** (Port 8490) - Data construction specialist
- **OpenAI Integration** (Port 8475) - AI integration specialist
- **Claude Task Hierarchy** (Port 8474) - Task construction specialist
- **Hierarchical Task System** (Port 8471) - System construction specialist

## Quick Start

### Prerequisites

- Python 3.8+
- At least 4GB RAM available
- Network access to service ports

### Installation

1. **Install dependencies:**
```bash
cd /home/activeloguser/activelog/services/unified-generative-gateway
pip3 install -r requirements.txt
```

2. **Start the network:**
```bash
./start_gateway.sh
```

3. **Access the dashboard:**
Open http://localhost:8601 in your browser

### Usage

#### Starting a Construction Project

```bash
curl -X POST http://localhost:8600/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "architect_001",
    "project_type": "construction_blueprint",
    "description": "Design a sustainable office building with smart systems",
    "requirements": {
      "floors": 5,
      "capacity": 200,
      "sustainability_features": true
    },
    "quality_tier": "professional",
    "deliverables": ["blueprints", "3d_model", "specifications"]
  }'
```

#### Checking Network Status

```bash
curl http://localhost:8600/network-status
```

#### Viewing Service Health

```bash
curl http://localhost:8600/services
```

## API Documentation

### Main Endpoints

- `GET /` - Gateway status and information
- `POST /orchestrate` - Start a construction project
- `GET /network-status` - Comprehensive network status
- `GET /services` - List all building bots and specialties
- `GET /analytics` - Network analytics and metrics
- `POST /service-health` - Check specific service health

### Dashboard Endpoints

- `GET /` - Main dashboard interface
- `GET /api/overview` - Dashboard data API
- `WebSocket /ws` - Real-time updates

## Project Types

The gateway supports various construction project types:

- `construction_blueprint` - Complete building blueprints
- `architectural_design` - Architectural planning and design
- `infrastructure_planning` - Infrastructure development
- `smart_building` - Smart building systems
- `sustainable_construction` - Eco-friendly construction
- `industrial_facility` - Industrial building design
- `residential_complex` - Residential development
- `commercial_building` - Commercial construction
- `renovation_project` - Building renovation
- `landscape_design` - Landscape architecture

## Quality Tiers

- `draft` - Basic quality for quick prototypes
- `standard` - Standard professional quality
- `high` - High quality with enhanced features
- `professional` - Professional-grade deliverables
- `excellence` - Premium quality with all enhancements

## Building Bots Network Mission

The Building Bots Network operates under the mission of **construction excellence through intelligent coordination**. Key principles:

1. **Quality First** - Every output meets professional construction standards
2. **Collaborative Excellence** - Bots work together seamlessly
3. **Innovation-Driven** - Leveraging cutting-edge AI for construction
4. **Efficiency Optimized** - Maximum value with optimal resource usage
5. **User-Centric** - Solutions tailored to user needs and preferences

## Monitoring & Management

### Real-time Dashboard Features

- **Network Health Matrix** - Visual service health overview
- **Performance Metrics** - CPU, memory, and response time tracking
- **Project Analytics** - Success rates and quality trends
- **Resource Utilization** - System resource monitoring
- **Service Specialties** - Building bot capability overview

### Service Management

The orchestrator automatically:
- Starts services in optimal order
- Monitors service health continuously
- Restarts failed services automatically
- Balances load across services
- Tracks performance metrics

### Log Files

- `Gateway.log` - Main gateway operations
- `Dashboard.log` - Dashboard service logs
- `orchestrator.log` - Service orchestration logs
- Individual service logs in respective directories

## Configuration

### Environment Variables

- `GATEWAY_PORT` - Main gateway port (default: 8600)
- `DASHBOARD_PORT` - Dashboard port (default: 8601)
- `ORCHESTRATOR_ENABLED` - Enable automatic orchestration (default: true)

### Service Configuration

Services are configured in the main gateway file with:
- Port assignments
- Health check endpoints
- Startup commands
- Building specialties
- Priority levels

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   - Check for existing processes: `lsof -i :8600`
   - Stop conflicting services or change ports

2. **Service Won't Start**
   - Check service logs for errors
   - Verify dependencies are installed
   - Ensure sufficient system resources

3. **Health Checks Failing**
   - Verify service is responding on correct port
   - Check network connectivity
   - Review service-specific logs

### Debugging

Enable debug logging by setting:
```bash
export LOG_LEVEL=DEBUG
```

### Service Recovery

If a service becomes unresponsive:
1. Check the dashboard for service status
2. Review service logs for errors
3. Restart individual services if needed
4. The orchestrator will attempt automatic recovery

## Development

### Adding New Services

1. Add service configuration to `BBN_SERVICES` in `main.py`
2. Update startup order in `orchestrator.py`
3. Add health check endpoint mapping
4. Test integration with existing services

### Extending Functionality

- **Custom Project Types** - Add to `ProjectType` enum
- **New Quality Tiers** - Extend `QualityTier` enum  
- **Additional Metrics** - Enhance monitoring systems
- **Custom Orchestration** - Modify orchestration logic

## Security Considerations

- Services run on localhost by default
- No external authentication by default
- Consider adding API keys for production
- Monitor resource usage to prevent abuse
- Review logs regularly for security issues

## Performance Optimization

### Resource Management
- Monitor memory usage across services
- Implement service scaling as needed
- Use connection pooling for HTTP requests
- Cache frequently accessed data

### Network Optimization
- Services communicate via localhost
- Use async/await for concurrent operations
- Implement request timeouts appropriately
- Balance load across service instances

## Support

For issues with the Building Bots Network:

1. Check service logs for error messages
2. Review the dashboard for system status
3. Verify system requirements are met
4. Test individual services independently

The Building Bots Network is designed for **construction excellence** - if you encounter issues, the network will attempt self-healing through automatic service management and intelligent routing.

---

**🏗️ Building Bots Network - Constructing the Future with AI Excellence**