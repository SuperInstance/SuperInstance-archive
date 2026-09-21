# FishingLog Crew Management Service

Comprehensive crew management system for fishing vessels running on port 8375.

## Features

### 🧑‍🤝‍🧑 Crew Management
- **Crew invitation system** with email-based invitations and token validation
- **Role-based permissions** with 8 distinct crew roles (Captain, First Mate, Engineer, Cook, Deck Hand, etc.)
- **Emergency contact management** and crew member profiles

### 🧭 Navigation Integration
- **Shared navigation view** with real-time data sharing across crew stations
- **Fish count display** integrated with navigation systems
- **Permission-based data filtering** for different crew roles
- **Real-time WebSocket updates** for live navigation data

### ⚠️ Watch & Alarm System
- **Watch alarm system** with attention monitoring (5-minute default intervals)
- **Escalating alarm system** with progressive alert levels (Info → Warning → Urgent → Critical → Emergency)
- **Captain override controls** for emergency situations
- **Automatic attention checks** with configurable intervals

### 📋 Task Management
- **Comprehensive task system** with categories, priorities, and assignments
- **Task templates** for recurring operations (safety drills, maintenance, etc.)
- **Progress tracking** with checklist items and notes
- **Dependency management** and automatic task scheduling

### 📅 Shift Scheduling
- **Maritime-compliant scheduling** with rest period enforcement
- **Role-based shift templates** (Watch, Engine Room, Galley, etc.)
- **Conflict detection** and resolution
- **Rotation pattern management**

### 💰 Crew Share Calculator
- **Flexible share schemes** (Equal, Role-based, Performance, Hybrid)
- **Automatic deduction handling** (Fuel, Ice, Food, Gear, etc.)
- **Bonus calculation** (Safety, Performance, Overtime, etc.)
- **Payment tracking** and crew earnings history

### 🛡️ Safety Drill Tracking
- **Comprehensive drill management** for all safety requirements
- **Regulatory compliance tracking** (SOLAS, STCW, USCG)
- **Performance evaluation** and improvement tracking
- **Automated scheduling** based on regulatory requirements

## API Endpoints

### Crew Management
- `POST /crew/invite` - Invite new crew member
- `POST /crew/accept-invitation` - Accept crew invitation
- `GET /crew/vessel/{vessel_id}` - Get vessel crew list

### Navigation
- `POST /navigation/register-station` - Register navigation station
- `POST /navigation/update` - Update navigation data
- `POST /navigation/fish-count` - Add fish count

### Alarms & Watch
- `POST /alarms/start-watch` - Start watch session
- `POST /alarms/end-watch/{watch_id}` - End watch session
- `POST /alarms/respond/{alarm_id}` - Respond to alarm
- `POST /alarms/override/{alarm_id}` - Override alarm (captain only)

### Task Management
- `POST /tasks` - Create new task
- `GET /tasks/user/{user_id}` - Get user tasks
- `POST /tasks/{task_id}/start` - Start task
- `POST /tasks/{task_id}/complete` - Complete task

### Shift Scheduling
- `POST /shifts` - Create new shift
- `GET /shifts/vessel/{vessel_id}` - Get vessel schedule
- `POST /shifts/{shift_id}/assign` - Assign crew to shift

### Share Calculator
- `POST /shares/calculate` - Calculate crew shares
- `GET /shares/trip/{trip_id}` - Get trip share summary
- `GET /shares/crew/{crew_id}` - Get crew member earnings

### Safety Drills
- `POST /drills` - Schedule safety drill
- `GET /drills/vessel/{vessel_id}` - Get vessel drills
- `GET /drills/compliance/{vessel_id}` - Get compliance status

## Real-time Features

### WebSocket Connection
Connect to `ws://localhost:8375/ws/{connection_id}` for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8375/ws/station-bridge-1');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'navigation_update':
      updateNavigationDisplay(data.navigation_data);
      break;
    case 'new_alarm':
      showAlarmNotification(data.alarm);
      break;
    case 'task_update':
      updateTaskList(data.task);
      break;
    case 'shift_update':
      updateScheduleDisplay(data.shift);
      break;
  }
};
```

### Supported Update Types
- `navigation_update` - Real-time navigation data
- `fish_count_update` - Fish catch updates  
- `new_alarm` - New alarm notifications
- `alarm_update` - Alarm status changes
- `watch_update` - Watch status changes
- `task_update` - Task assignments/completions
- `shift_update` - Schedule changes
- `drill_update` - Safety drill updates

## Installation & Setup

### Requirements
- Python 3.11+
- FastAPI 0.104+
- SQLite/PostgreSQL database
- Redis (for real-time features)

### Installation
```bash
cd /home/activeloguser/activelog/services/fishinglog-crew
pip install -r requirements.txt
```

### Configuration
Create `.env` file:
```env
PORT=8375
DATABASE_URL=sqlite:///./fishinglog_crew.db
SECRET_KEY=your-secret-key-here
SMTP_SERVER=smtp.example.com
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-email-password
REDIS_URL=redis://localhost:6379/0
```

### Running the Service
```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 8375 --reload
```

## Architecture

### Core Components

1. **CrewManager** - Handles crew invitations and member management
2. **PermissionManager** - Role-based access control system
3. **SharedNavigationManager** - Real-time navigation data sharing
4. **WatchAlarmManager** - Watch duties and alarm escalation
5. **TaskManager** - Task assignment and tracking
6. **ShiftScheduler** - Crew scheduling with compliance
7. **ShareCalculator** - Crew compensation calculation
8. **DrillTracker** - Safety drill management and compliance

### Data Models

#### Crew Roles
- **Captain** - Full system access, override capabilities
- **First Mate** - Navigation, watch supervision, task assignment
- **Engineer** - Engine room operations, maintenance tasks
- **Cook** - Galley operations, food safety
- **Deck Hand** - General deck operations, fishing activities
- **Radio Operator** - Communications, emergency procedures
- **Safety Officer** - Safety compliance, drill coordination
- **Guest** - Limited access, observation only

#### Permission System
- **Global** - System-wide permissions
- **Vessel** - Vessel-specific permissions
- **Trip** - Trip-specific permissions  
- **Watch** - Watch-specific permissions

### Integration Points

The service integrates with:
- **FishingLog Core** (Port 8001) - Trip and vessel data
- **Auth Service** (Port 8002) - User authentication
- **Navigation Service** (Port 8003) - Real-time navigation data
- **Communication systems** - Email, SMS notifications
- **External APIs** - Weather, market data

## Safety & Compliance

### Maritime Regulations
- **SOLAS** compliance for safety drills
- **STCW** certification tracking
- **USCG** regulation adherence
- **Work/rest hour** compliance monitoring

### Drill Requirements
- **Weekly** fire drills
- **Monthly** abandon ship drills
- **Quarterly** man overboard/damage control
- **Biannual** medical emergency drills

### Data Security
- Role-based access control
- Encrypted communication
- Audit trail logging
- Secure invitation system

## Development

### Testing
```bash
pytest tests/
```

### Code Quality
```bash
black .
flake8 .
mypy .
```

### API Documentation
Visit `http://localhost:8375/docs` for interactive API documentation.

## Monitoring

- Health check endpoint: `GET /health`
- Metrics endpoint: `GET /metrics` (if enabled)
- Real-time statistics: `GET /stats/vessel/{vessel_id}`

## Support

For questions or issues with the FishingLog Crew Management Service, please contact the development team or refer to the main FishingLog documentation.