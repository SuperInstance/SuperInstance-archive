# Child Safety System

A comprehensive child safety and protection system with content filtering, interaction monitoring, bullying prevention, screen time management, health monitoring, emergency contacts, and COPPA compliance.

## Features

### 🛡️ Content Filtering
- Age-appropriate content filtering with customizable ratings
- Educational value assessment and scoring
- Real-time content analysis and blocking
- Parent override request system
- Category-based filtering (violence, adult content, inappropriate language)

### 👁️ Interaction Monitoring
- Privacy-respecting interaction analysis
- Pattern-based risk detection without storing personal content
- Real-time safety alerts for concerning behavior
- Anonymized metadata tracking with automatic data expiration
- Behavioral pattern analysis for safety threats

### 🚫 Bullying Prevention
- Comprehensive bullying detection using multiple indicators
- Severity assessment and intervention strategies
- Educational interventions and positive behavior reinforcement
- Parent and authority notifications for serious incidents
- Peer support network facilitation

### ⏰ Screen Time Management
- Age-appropriate screen time limits with flexible scheduling
- Educational content bonus time allocation
- Comprehensive break reminder system (micro, short, long breaks)
- Activity-based time tracking and management
- Parent-controlled extensions and override system

### 🏥 Health Monitoring
- Digital wellness monitoring (eye strain, posture, fatigue)
- Proactive health interventions and break reminders
- Learning effectiveness and cognitive load assessment
- Physical activity encouragement and hydration reminders
- Comprehensive health dashboard and reporting

### 🚨 Emergency Contact System
- Multi-tiered emergency contact management
- Automated emergency response protocols
- Multiple contact methods (email, SMS, phone, app notifications)
- Escalation procedures for unresponded incidents
- Integration with emergency services when necessary

### 📋 COPPA Compliance
- Automated age verification and parental consent management
- Comprehensive data collection tracking and retention policies
- Parental consent verification through multiple methods
- Data deletion automation and compliance auditing
- Regulatory reporting and violation detection

## Architecture

```
child-safety/
├── content_filtering/          # Age-appropriate content filtering
│   └── age_appropriate_filter.py
├── monitoring/                 # Privacy-respecting interaction monitoring
│   └── privacy_respecting_monitor.py
├── bullying_prevention/        # Bullying detection and intervention
│   └── anti_bullying_system.py
├── screen_time/               # Screen time management and limits
│   └── screen_time_manager.py
├── health/                    # Digital health monitoring
│   └── health_monitor.py
├── emergency/                 # Emergency contact system
│   └── emergency_contacts.py
├── compliance/                # COPPA compliance automation
│   └── coppa_compliance.py
├── main.py                   # FastAPI main service
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## API Endpoints

### User Management
- `POST /users/register` - Register new user with safety protections
- `GET /safety/dashboard/{user_id}` - Get comprehensive safety dashboard

### Content Safety
- `POST /content/filter` - Filter content for age-appropriateness
- `POST /interactions/monitor` - Monitor user interactions for safety

### Screen Time
- `POST /screentime/start` - Start screen time session
- `POST /screentime/end/{session_id}` - End screen time session

### Health Monitoring  
- `GET /health/dashboard/{user_id}` - Get health monitoring dashboard

### Emergency System
- `POST /emergency/contacts` - Add emergency contact
- `POST /emergency/alert` - Trigger emergency alert

### COPPA Compliance
- `POST /coppa/consent` - Request parental consent
- `GET /coppa/compliance/{user_id}` - Get compliance status

### Administration
- `POST /admin/audit` - Run compliance audit
- `POST /admin/data-retention` - Run data retention review

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up PostgreSQL database and configure environment variables:
```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=child_safety
export DB_USER=postgres
export DB_PASSWORD=your_password
```

3. Start the service:
```bash
python main.py
```

The service will be available at `http://localhost:8213`

## Database Setup

The system automatically creates all necessary database tables on startup. Ensure PostgreSQL is running and accessible with the configured credentials.

## Safety Features

### Multi-Layer Protection
- **Proactive Filtering**: Content is filtered before reaching the child
- **Real-Time Monitoring**: Interactions are monitored for safety concerns  
- **Intervention System**: Automatic and manual interventions for safety issues
- **Parent Integration**: Parents are kept informed and can override restrictions
- **Emergency Response**: Immediate response capability for critical situations

### Privacy Protection
- **Data Minimization**: Only necessary data is collected and stored
- **Anonymization**: Personal data is anonymized where possible
- **Retention Limits**: Data is automatically deleted based on retention policies
- **Consent Management**: Full parental consent tracking and management
- **Access Controls**: Strict access controls for all sensitive data

### Compliance
- **COPPA Compliant**: Full compliance with Children's Online Privacy Protection Act
- **Data Protection**: Comprehensive data protection and privacy controls
- **Audit Trail**: Complete audit trail for all data collection and processing
- **Regulatory Reporting**: Automated compliance reporting and violation detection

## Usage Examples

### Register a Child User
```python
POST /users/register
{
    "user_id": "child_123",
    "age": 8,
    "birth_date": "2015-06-15",
    "parental_email": "parent@example.com",
    "parent_name": "Jane Doe"
}
```

### Filter Content
```python
POST /content/filter
{
    "content": "Educational video about science experiments",
    "content_type": "video",
    "source_url": "https://education.example.com/science"
}
```

### Add Emergency Contact
```python
POST /emergency/contacts
{
    "user_id": "child_123",
    "contact_type": "parent",
    "name": "Jane Doe",
    "relationship": "mother",
    "email": "jane.doe@example.com",
    "phone_primary": "+1-555-0123",
    "can_authorize": true
}
```

## Monitoring and Alerts

The system provides comprehensive monitoring and alerting:

- **Real-time Safety Alerts**: Immediate notifications for safety concerns
- **Health Monitoring**: Continuous digital wellness monitoring
- **Compliance Alerts**: Automated compliance violation detection
- **Emergency Notifications**: Multi-channel emergency contact system
- **Parent Dashboard**: Comprehensive parent visibility and control

## Development

For development mode, set `reload=True` in the uvicorn run command:

```python
uvicorn.run("main:app", host="0.0.0.0", port=8213, reload=True)
```

## Security Considerations

- All sensitive data is encrypted at rest and in transit
- Authentication and authorization controls protect all endpoints
- Rate limiting prevents abuse of the system
- Comprehensive logging and audit trails
- Regular security assessments and updates

## Support

For issues, questions, or feature requests, please contact the development team or create an issue in the project repository.