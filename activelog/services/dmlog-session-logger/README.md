# DMLog Session Logger

A simple D&D session logging application with dice rolling and character tracking features.

## Features

- **Session Notes**: Track session details with titles, notes, and dates
- **Dice Roller**: Roll common dice (d4, d6, d8, d10, d12, d20, d100) or custom combinations
- **Character Tracker**: Manage characters with name, class, level, HP, and notes
- **Health Check**: `/health` endpoint for monitoring
- **Responsive Design**: Works on desktop and mobile devices

## Deployment

This service is configured for deployment using the ActiveLog deployment pipeline.

### Local Development

```bash
cd /home/activeloguser/activelog/services/dmlog-session-logger
pip3 install -r requirements.txt
python3 main.py
```

The service will run on port 8002 by default, or the port specified in the `PORT` environment variable.

### Production Deployment

Use the ActiveLog deployment script:

```bash
# Deploy to EC2 (requires proper EC2_HOST and EC2_KEY configuration)
./deploy.sh dmlog-session-logger --host ubuntu@34.223.235.20 --key ~/.ssh/personallog_key

# Or set environment variables
EC2_HOST=ubuntu@34.223.235.20 EC2_KEY=~/.ssh/personallog_key ./deploy.sh dmlog-session-logger
```

The deployment script will:
1. Detect this as a Python service
2. Upload all service files to EC2
3. Create a startup script with port 8002 (or auto-assigned port)
4. Configure nginx proxy
5. Start the service
6. Provide access URLs

### API Endpoints

- `GET /` - Main web interface
- `GET /health` - Health check endpoint
- `GET /sessions` - Get all sessions
- `POST /sessions` - Create new session
- `GET /characters` - Get all characters  
- `POST /characters` - Create new character
- `GET /roll/{dice}` - Roll dice (e.g., /roll/2d6, /roll/d20)

### Data Storage

Session and character data is stored in local JSON files:
- `sessions.json` - Session notes
- `characters.json` - Character data

## Service Configuration

- **Port**: 8002 (configurable via PORT environment variable)
- **Service Type**: Python Flask application
- **Dependencies**: Flask, Werkzeug, Jinja2
- **Health Check**: Available at `/health` endpoint
- **Templates**: Located in `templates/` directory