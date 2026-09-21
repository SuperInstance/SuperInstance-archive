# ActiveLog Authentication Service

A comprehensive JWT-based authentication service for the ActiveLog ecosystem. Provides secure user management, token-based authentication, and cross-service integration.

## 🚀 Features

- **User Registration & Login** - Secure account creation and authentication
- **JWT Token Management** - Access tokens with refresh token support
- **Password Security** - bcrypt hashing with strong password requirements
- **Rate Limiting** - Protection against brute force attacks
- **Security Audit** - Comprehensive logging of security events
- **Service Access Control** - Fine-grained permissions per service
- **Cross-Service Integration** - Middleware and client libraries for easy integration
- **Account Security** - Account lockout, failed attempt tracking
- **Profile Management** - User profile and service access management

## 📋 API Endpoints

### Authentication
- `POST /api/register` - Register new user account
- `POST /api/login` - Login user and get tokens
- `POST /api/refresh` - Refresh access token
- `POST /api/logout` - Logout user
- `POST /api/validate-token` - Validate JWT token (for other services)

### User Management
- `GET /api/me` - Get current user profile
- `POST /api/grant-service/{service_name}` - Grant service access

### System
- `GET /api/health` - Health check
- `GET /api/metrics` - Service metrics

## 🔧 Quick Start

### 1. Start the Authentication Service

```bash
# Using deploy.sh
./deploy.sh auth-service --host ubuntu@your-server.com --key ~/.ssh/your-key.pem

# Or run locally
cd services/auth-service
python main.py --port 8080
```

### 2. Register a User

```bash
curl -X POST "http://localhost:8080/api/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "username": "testuser",
    "full_name": "Test User"
  }'
```

### 3. Login

```bash
curl -X POST "http://localhost:8080/api/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

## 🔌 Integration with Other Services

### Method 1: Using Middleware (Recommended)

```python
from fastapi import FastAPI
from auth_service.middleware import AuthMiddleware

app = FastAPI()

# Add authentication middleware
app.add_middleware(AuthMiddleware, auth_service_url="http://localhost:8080")

@app.get("/api/protected")
async def protected_route(request: Request):
    user = getattr(request.state, 'current_user', None)
    return {"message": f"Hello {user['username']}"}
```

### Method 2: Using Dependencies

```python
from fastapi import FastAPI, Depends
from auth_service.middleware import get_current_user

app = FastAPI()

@app.get("/api/protected")
async def protected_route(current_user: dict = Depends(get_current_user)):
    return {"message": f"Hello {current_user['username']}"}
```

### Method 3: Using Client Library

```python
from auth_service.client import create_auth_client

auth_client = create_auth_client("http://localhost:8080")

# Validate token
user = await auth_client.validate_token(token)
if user:
    print(f"Authenticated user: {user['username']}")
```

## 🛡️ Security Features

### Password Requirements
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter  
- At least one digit
- At least one special character

### Rate Limiting
- **Login attempts**: 5 per hour per IP
- **Registration attempts**: 3 per hour per IP
- **Account lockout**: 1 hour after 5 failed login attempts

### Token Security
- **Access tokens**: 24 hours expiration
- **Refresh tokens**: 7 days expiration
- **Secure storage**: Tokens hashed in database
- **Token validation**: Cross-service validation endpoint

## 📊 Database Schema

### Users Table
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    services TEXT DEFAULT '[]'
);
```

### Refresh Tokens Table
```sql
CREATE TABLE refresh_tokens (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    device_info TEXT,
    ip_address TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
```

### Security Audit Table
```sql
CREATE TABLE security_audit (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    event_type TEXT NOT NULL,
    event_details TEXT,
    ip_address TEXT,
    user_agent TEXT,
    success BOOLEAN,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

## 🔧 Configuration

### Environment Variables

```bash
# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
AUTH_DATABASE_PATH=auth_data.db

# Rate Limiting
RATE_LIMIT_WINDOW=3600  # 1 hour
MAX_LOGIN_ATTEMPTS=5
MAX_REGISTRATION_ATTEMPTS=3

# Service
PORT=8080
HOST=0.0.0.0
SERVICE_NAME=auth-service

# Security
ACCOUNT_LOCKOUT_DURATION=3600  # 1 hour
PASSWORD_MIN_LENGTH=8
REQUIRE_EMAIL_VERIFICATION=false

# CORS
CORS_ORIGINS=*

# Logging
LOG_LEVEL=INFO
LOG_FILE=auth_service.log
```

## 🧪 Testing

### Test Authentication Flow

```python
import asyncio
from auth_service.client import create_auth_client

async def test_auth():
    client = create_auth_client("http://localhost:8080")
    
    # Register user
    result = await client.register_user(
        email="test@example.com",
        password="TestPassword123!",
        username="testuser",
        full_name="Test User"
    )
    
    if result:
        token = result['access_token']
        print(f"Registration successful, token: {token[:20]}...")
        
        # Validate token
        user = await client.validate_token(token)
        print(f"Token valid for user: {user['username']}")

# Run test
asyncio.run(test_auth())
```

### Test with curl

```bash
# Register
REGISTER_RESPONSE=$(curl -s -X POST "http://localhost:8080/api/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "username": "testuser",
    "full_name": "Test User"
  }')

# Extract token
TOKEN=$(echo $REGISTER_RESPONSE | jq -r '.access_token')

# Test protected endpoint
curl -X GET "http://localhost:8080/api/me" \
  -H "Authorization: Bearer $TOKEN"
```

## 📈 Metrics & Monitoring

The service provides comprehensive metrics at `/api/metrics`:

```json
{
  "service": "ActiveLog Authentication Service",
  "status": "healthy",
  "metrics": {
    "total_users": 150,
    "active_users": 142,
    "verified_users": 128,
    "logins_last_24h": 45
  },
  "database": {
    "path": "auth_data.db",
    "exists": true
  },
  "timestamp": "2025-08-26T13:22:00Z"
}
```

## 🔄 Integration Examples

### Modify Existing PersonalLog Service

```python
# Add to existing main.py
from auth_service.middleware import AuthMiddleware

# Add middleware
app.add_middleware(AuthMiddleware, auth_service_url="http://localhost:8080")

# Modify existing endpoints
@app.post("/api/entries")
async def create_entry(entry: JournalEntry, request: Request):
    user = getattr(request.state, 'current_user', None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    entry.user_id = user['id']  # Associate with authenticated user
    return await backend.create_entry(entry)
```

### Service Access Control

```python
# Grant user access to specific services
await auth_client.grant_service_access(token, "personallog")
await auth_client.grant_service_access(token, "fishinglog")
await auth_client.grant_service_access(token, "dmlog")

# Check access in service
user_services = user.get('services', [])
if "personallog" not in user_services:
    raise HTTPException(status_code=403, detail="Access denied")
```

## 🚀 Deployment

The service is designed to work with the ActiveLog deployment pipeline:

```bash
# Deploy to EC2
./deploy.sh auth-service --host ubuntu@your-server.com --key ~/.ssh/your-key.pem

# The service will be available at:
# - Direct: http://your-server:8400
# - Proxy: https://activelog.ai/auth-service/
```

## 🔐 Security Best Practices

1. **Use strong JWT secrets** in production
2. **Enable HTTPS** for all authentication endpoints
3. **Implement proper CORS** policies
4. **Monitor security logs** regularly
5. **Rotate tokens** periodically
6. **Use secure password policies**
7. **Implement account verification** for production

## 📝 License

Part of the ActiveLog ecosystem. See main project for license details.

## 🤝 Contributing

This is a core security service - all changes should be thoroughly reviewed and tested.