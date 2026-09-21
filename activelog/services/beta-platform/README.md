# ActiveLog Beta Platform

A comprehensive beta testing platform with user feedback collection, bug reporting, feature request voting, rewards system, staged rollouts, performance monitoring, crash reporting, usage analytics, A/B testing framework, and documentation.

## Features

### 🗣️ User Feedback Collection
- Structured feedback with ratings (1-5 stars)
- Categories: UI, Performance, Feature, General
- Priority levels: Low, Medium, High, Critical
- Status tracking: Open, Reviewed, Implemented, Closed

### 🐛 Bug Reporting with Screenshots
- Detailed bug reports with reproduction steps
- Screenshot upload support
- Browser and device information capture
- Severity levels: Low, Medium, High, Critical
- Status tracking: Open, Investigating, Fixed, Closed

### 💡 Feature Request Voting System
- Submit feature requests with detailed descriptions
- Community voting (upvote/downvote)
- Priority and effort estimation
- Business value assessment
- Status tracking: Proposed, Approved, In Progress, Completed, Rejected

### 🏆 Beta Tester Rewards System
- Point-based reward system
- Activity tracking and automatic point awards
- Leaderboards and ranking
- Tier system: Basic, Premium, Enterprise
- Point redemption for rewards

### 🚀 Staged Rollout Management
- Feature flag management
- User targeting and percentage rollouts
- Rollout metrics tracking
- Stage-based deployments

### 📊 Performance Monitoring
- Performance metric collection
- Page load times, API response times
- Memory usage tracking
- Performance statistics and analysis

### 💥 Crash Reporting
- Automatic crash detection and reporting
- Stack trace collection
- Error categorization
- Severity assessment

### 📈 Usage Analytics
- Event tracking (page views, clicks, feature usage)
- User behavior analysis
- Session tracking
- Usage statistics and insights

### 🧪 A/B Testing Framework
- Create and manage A/B tests
- Variant assignment and traffic allocation
- Result collection and analysis
- Statistical significance testing

### 📚 Beta Documentation
- Comprehensive API documentation
- Getting started guides
- FAQ section
- Interactive documentation portal

## Installation

### Using Docker Compose (Recommended)

```bash
cd ~/activelog/services/beta-platform
docker-compose up -d
```

### Manual Installation

1. **Install Dependencies**
```bash
cd ~/activelog/services/beta-platform
pip install -r requirements.txt
```

2. **Set up Environment Variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Set up Database**
```bash
# Make sure PostgreSQL is running
createdb activelog_beta
```

4. **Start the Server**
```bash
./start.sh
# Or manually:
python -m uvicorn src.main:app --host 0.0.0.0 --port 8323 --reload
```

## API Endpoints

### Feedback (`/api/feedback`)
- `POST /submit` - Submit new feedback
- `GET /` - Get feedback list with filtering
- `GET /{id}` - Get specific feedback
- `PUT /{id}/status` - Update feedback status
- `GET /stats/summary` - Get feedback statistics

### Bug Reports (`/api/bugs`)
- `POST /submit` - Submit bug report with screenshots
- `GET /` - Get bug reports with filtering
- `GET /{id}` - Get specific bug report
- `PUT /{id}/status` - Update bug status
- `GET /stats/summary` - Get bug statistics

### Feature Requests (`/api/features`)
- `POST /submit` - Submit feature request
- `GET /` - Get feature requests with sorting
- `GET /{id}` - Get specific feature request
- `POST /{id}/vote` - Vote on feature (upvote/downvote)
- `GET /{id}/votes` - Get vote details
- `PUT /{id}/status` - Update feature status
- `GET /stats/summary` - Get feature statistics

### Rewards (`/api/rewards`)
- `POST /award` - Award points to user
- `GET /user/{id}/balance` - Get user point balance
- `GET /user/{id}/transactions` - Get transaction history
- `GET /leaderboard` - Get rewards leaderboard
- `GET /user/{id}/summary` - Get comprehensive reward summary
- `GET /tiers` - Get reward tiers information
- `POST /redeem` - Redeem points for rewards

### Rollout Management (`/api/rollout`)
- `POST /stages` - Create rollout stage
- `GET /stages` - Get rollout stages
- `PUT /stages/{id}/activate` - Activate rollout stage
- `GET /user/{id}/features` - Get user's feature flags

### Performance Monitoring (`/api/monitoring`)
- `POST /performance` - Record performance metric
- `GET /performance/stats` - Get performance statistics

### Crash Reporting (`/api/crashes`)
- `POST /submit` - Submit crash report
- `GET /` - Get crash reports with filtering
- `GET /stats` - Get crash statistics

### Usage Analytics (`/api/analytics`)
- `POST /track` - Track usage event
- `GET /events` - Get usage events with filtering
- `GET /stats` - Get usage statistics

### A/B Testing (`/api/ab-testing`)
- `POST /tests` - Create A/B test
- `GET /tests` - Get A/B tests
- `POST /tests/{id}/start` - Start A/B test
- `GET /tests/{id}/assign/{user_id}` - Assign user to variant
- `POST /tests/{id}/results` - Record test result
- `GET /tests/{id}/analysis` - Get test analysis

### Documentation (`/api/docs`)
- `GET /` - Documentation home page
- `GET /api-docs` - API documentation
- `GET /getting-started` - Getting started guide
- `GET /faq` - Frequently asked questions

## Configuration

### Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/activelog_beta

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# File Upload
MAX_FILE_SIZE=10485760  # 10MB
UPLOAD_DIR=static/uploads

# Server
HOST=0.0.0.0
PORT=8323
DEBUG=True
```

### Database Schema

The platform automatically creates the following tables:
- `beta_users` - User information and beta tester details
- `feedback` - User feedback submissions
- `bug_reports` - Bug reports with screenshot support
- `feature_requests` - Feature requests and voting
- `feature_votes` - Individual votes on features
- `reward_transactions` - Point transactions and rewards
- `rollout_stages` - Staged rollout configuration
- `user_rollout_assignments` - User assignments to rollout stages
- `rollout_metrics` - Rollout performance metrics
- `crash_reports` - Crash reports and error tracking
- `performance_metrics` - Performance monitoring data
- `usage_events` - Usage analytics events
- `ab_tests` - A/B test configurations
- `ab_test_assignments` - User assignments to test variants
- `ab_test_results` - A/B test results and metrics

## Usage Examples

### Submit Feedback
```python
import httpx

response = httpx.post("http://localhost:8323/api/feedback/submit", json={
    "user_id": "user-uuid",
    "category": "ui",
    "rating": 4,
    "title": "Great new feature!",
    "description": "The new dashboard is very intuitive",
    "priority": "medium"
})
```

### Report Bug with Screenshot
```python
import httpx

files = {"screenshots": open("bug_screenshot.png", "rb")}
data = {
    "user_id": "user-uuid",
    "title": "Button not working",
    "description": "The save button doesn't respond to clicks",
    "severity": "high",
    "steps_to_reproduce": "1. Click save button 2. Nothing happens"
}

response = httpx.post("http://localhost:8323/api/bugs/submit", data=data, files=files)
```

### Vote on Feature Request
```python
import httpx

response = httpx.post("http://localhost:8323/api/features/{feature_id}/vote", json={
    "user_id": "user-uuid",
    "vote_type": "upvote"
})
```

### Track Usage Event
```python
import httpx

response = httpx.post("http://localhost:8323/api/analytics/track", json={
    "user_id": "user-uuid",
    "event_type": "button_click",
    "event_data": {"button": "save", "page": "dashboard"},
    "url": "/dashboard",
    "session_id": "session-uuid"
})
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Structure
```
src/
├── main.py                 # FastAPI application and routing
├── database.py             # Database models and connection
├── feedback/               # Feedback collection module
├── bug_reporting/          # Bug reporting module  
├── feature_requests/       # Feature requests and voting
├── rewards/                # Rewards and points system
├── rollout/                # Staged rollout management
├── monitoring/             # Performance monitoring
├── crash_reporting/        # Crash reporting
├── analytics/              # Usage analytics
├── ab_testing/             # A/B testing framework
└── documentation/          # Documentation endpoints
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is part of the ActiveLog platform and follows the same licensing terms.