# ActiveWorkLog Coordination System

The **ActiveWorkLog Coordination System** is the central coordination hub for the Building Bots Network, enabling intelligent coordination, conflict prevention, and seamless task continuity across all bot operations.

## 🎯 Core Purpose

Solves the critical problem: **"we need an 'I'm still here and working on the following' folder where each bot leaves an updated report of all information needed for another bot to come behind them if the worker dies in the process."**

## 🚀 Key Features

### 1. Work Registration & Coordination
- **Conflict Detection**: Automatically detects resource conflicts and task overlaps
- **Priority Management**: Intelligent priority-based task scheduling
- **Dependency Tracking**: Manages task dependencies and prerequisites

### 2. Bot Continuity & Handoffs
- **Seamless Handoffs**: Transfer work between bots with full context preservation
- **Checkpoint System**: Maintains detailed checkpoint data for task resumption
- **Failure Recovery**: Automatic detection and recovery from bot failures

### 3. Resource Management
- **Resource Locking**: Prevents conflicts over files, services, and APIs
- **Availability Checking**: Real-time resource availability validation
- **Shared Resource Support**: Configurable shared resource access

### 4. Network Monitoring
- **Real-time Visibility**: Live view of all bot activities across the network
- **Health Monitoring**: Network health scoring and stale work detection
- **Performance Analytics**: Coordination performance metrics and insights

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Bot Network   │────│  ActiveWorkLog   │────│  Coordination   │
│                 │    │   Coordinator    │    │   Database      │
│ • DMLog Bots    │    │                  │    │                 │
│ • Marine Bots   │    │ • Registration   │    │ • Work Entries  │
│ • Gaming Bots   │    │ • Conflicts      │    │ • Conflicts     │
│ • Business Bots │    │ • Handoffs       │    │ • Metrics       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────────┐
                    │   Network Monitor   │
                    │  & Health Dashboard │
                    └─────────────────────┘
```

## 🌐 API Endpoints

### Work Management
- `POST /work/register` - Register new work
- `PUT /work/{work_id}` - Update work progress
- `POST /work/{work_id}/complete` - Mark work as completed
- `POST /work/{work_id}/handoff` - Hand off work to another bot

### Coordination
- `GET /work/active` - Get all active work
- `POST /resources/check` - Check resource availability
- `GET /network/status` - Get network status
- `GET /work/{work_id}` - Get detailed work information

## 📊 Database Schema

### Work Entries Table
```sql
work_entries (
    work_id TEXT PRIMARY KEY,
    bot_name TEXT NOT NULL,
    task_description TEXT NOT NULL,
    resources TEXT,  -- JSON array of resources
    priority INTEGER,
    started_at TIMESTAMP,
    last_heartbeat TIMESTAMP,
    estimated_completion TIMESTAMP,
    progress_percentage REAL,
    status TEXT,
    metadata TEXT,  -- JSON object
    dependencies TEXT,  -- JSON array
    can_be_shared BOOLEAN,
    checkpoint_data TEXT  -- JSON object
)
```

### Conflict Detection
```sql
conflict_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work1_id TEXT,
    work2_id TEXT,
    conflict_type TEXT,
    severity TEXT,
    detected_at TIMESTAMP,
    resolved BOOLEAN DEFAULT FALSE,
    resolution_notes TEXT
)
```

## 🤖 Bot Integration Examples

### Registering Work
```python
import requests

# Register work with the coordination system
response = requests.post("http://localhost:8480/work/register", json={
    "bot_name": "dmlog-backend",
    "task_description": "Process user authentication and session management",
    "resources": ["/home/activeloguser/activelog/services/dmlog-backend", "database:auth"],
    "priority": 8,
    "estimated_duration_minutes": 30,
    "can_be_shared": False,
    "metadata": {"session_id": "auth_session_123"}
})

work_id = response.json()["work_id"]
```

### Updating Progress
```python
# Update work progress
requests.put(f"http://localhost:8480/work/{work_id}", json={
    "progress_percentage": 75.0,
    "status": "active",
    "checkpoint_data": {
        "authenticated_users": 150,
        "pending_validations": 3,
        "last_checkpoint": "user_validation_complete"
    }
})
```

### Checking Resource Conflicts
```python
# Check if resources are available before starting work
response = requests.post("http://localhost:8480/resources/check", json=[
    "/home/activeloguser/activelog/services/marine-autopilot",
    "gps:primary"
])

availability = response.json()
if availability["all_available"]:
    print("Resources available - can proceed")
else:
    print(f"Conflicts: {availability['resource_conflicts']}")
```

### Requesting Work Handoff
```python
# Hand off work to another bot (e.g., due to specialization needs)
response = requests.post(f"http://localhost:8480/work/{work_id}/handoff", 
    params={
        "new_bot_name": "marine-navigation-specialist",
        "reason": "Requires specialized navigation algorithms"
    }
)

handoff_data = response.json()
checkpoint_data = handoff_data["checkpoint_data"]  # Use this to resume work
```

## 🔧 Configuration

### Environment Variables
- `PORT` - Server port (default: 8480)
- `DB_PATH` - Database path (default: coordination.db)
- `HEARTBEAT_TIMEOUT` - Heartbeat timeout in seconds (default: 300)

### Work Priorities
- `1-3` - Low priority (background tasks)
- `4-6` - Normal priority (standard operations)
- `7-8` - High priority (important tasks)
- `9-10` - Critical priority (urgent/emergency tasks)

### Work Status Values
- `active` - Currently being worked on
- `paused` - Temporarily stopped
- `blocked` - Waiting for dependencies
- `completing` - In final stages
- `completed` - Finished successfully
- `abandoned` - No longer being worked on

## 📈 Monitoring & Analytics

### Network Health Metrics
- **Active Work Count**: Number of ongoing tasks
- **Active Bot Count**: Number of bots currently working
- **Stalled Work Detection**: Identifies abandoned or stuck tasks
- **Conflict Rate**: Frequency of resource/task conflicts
- **Handoff Success Rate**: Percentage of successful task transfers

### Performance Monitoring
- **Average Task Duration**: Time from registration to completion
- **Resource Utilization**: Usage patterns for shared resources
- **Bot Efficiency**: Task completion rates per bot
- **Network Load**: Overall system activity levels

## 🔍 Conflict Resolution

### Automatic Conflict Detection
1. **Resource Conflicts**: Multiple bots trying to use same exclusive resources
2. **Task Overlap**: Similar tasks being performed simultaneously
3. **Dependency Conflicts**: Circular or broken dependencies

### Resolution Strategies
1. **Priority-based**: Higher priority work gets precedence
2. **Time-based**: First-come, first-served for equal priorities
3. **Capability-based**: Route to most suitable bot
4. **Load-based**: Distribute work based on current bot loads

## 🎯 Building Bots Network Integration

### Supported Bot Types
- **DMLog Services**: Gaming, character management, session logging
- **Marine Services**: Navigation, autopilot, weather monitoring
- **Business Services**: Accounting, management, reporting
- **Development Services**: Code generation, testing, deployment
- **Infrastructure Services**: System monitoring, data management

### Network Coordination Benefits
- **Prevents Work Duplication**: Avoids multiple bots doing same task
- **Ensures Resource Safety**: Prevents file/service conflicts
- **Enables Specialization**: Routes work to most capable bots
- **Provides Continuity**: Maintains work during bot failures
- **Offers Visibility**: Real-time view of all network activity

## 🚀 Getting Started

### Installation
```bash
cd /home/activeloguser/activelog/services/activeworklog
pip install -r requirements.txt
```

### Running the System
```bash
python main.py
# Or with custom port:
PORT=8480 python main.py
```

### Testing the System
```bash
# Run comprehensive test suite
python test_client.py

# Run quick demo
python test_client.py demo
```

## 📊 Research & Analytics

### Data Collection
- All coordination activities are logged for analysis
- Performance metrics are collected in real-time
- Conflict patterns are tracked for optimization
- Network health trends are monitored continuously

### Academic Applications
- Multi-agent coordination research
- Distributed system performance analysis
- Conflict resolution algorithm development
- Network reliability studies

## 🔒 Security & Reliability

### Data Integrity
- Comprehensive audit trails for all activities
- Atomic operations for critical updates
- Automatic backup of coordination state
- Data validation and consistency checks

### Fault Tolerance
- Automatic detection of failed/stalled work
- Graceful handling of bot disconnections
- Recovery mechanisms for interrupted tasks
- Redundancy planning for critical operations

---

**ActiveWorkLog Coordination System** - Enabling Seamless Coordination Across the Building Bots Network