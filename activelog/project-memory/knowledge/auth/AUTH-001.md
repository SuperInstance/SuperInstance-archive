# AUTH-001: Authentication Service

**Type:** Core Service  
**Complexity:** High  
**Dependencies:** CORE-001, SEC-001  
**Last Updated:** 2025-08-26  

## Simple View (50 tokens)
Central JWT auth service with 2FA, API keys, role-based access. Handles login/logout, token validation, user management.

## Advanced View (200 tokens)
Authentication service (`services/auth/`) provides:
- **JWT Tokens**: Secure token generation/validation with configurable expiry
- **2FA Support**: Time-based OTP authentication for enhanced security
- **API Key Management**: Service-to-service authentication with scoped permissions
- **Role-Based Access**: User roles, permissions, access level enforcement
- **Session Management**: Redis-backed session storage, logout handling
- **Security Features**: Rate limiting, IP blocking, audit logging, threat assessment
- **Database**: SQLite user storage with encrypted passwords (bcrypt)
- **Middleware Integration**: Authentication middleware for all services

## Full Documentation

The authentication service serves as the central security hub for the entire ActiveLog ecosystem. It implements enterprise-grade security patterns while maintaining simplicity for development workflows.

### Core Components

#### JWT Token System
- **Generation**: Creates signed JWT tokens with user claims
- **Validation**: Middleware validates tokens on each request
- **Refresh**: Automatic token refresh before expiry
- **Revocation**: Token blacklisting for logout/security events

#### Two-Factor Authentication
- **TOTP Implementation**: Time-based one-time passwords using standard algorithms
- **Backup Codes**: Recovery codes for device loss scenarios  
- **QR Code Generation**: Easy mobile app setup
- **Enforcement**: Configurable 2FA requirements per user role

#### API Key Management
- **Generation**: Cryptographically secure key generation
- **Scoping**: Permission-based key restrictions
- **Rotation**: Automated and manual key rotation
- **Usage Tracking**: API key usage monitoring and analytics

#### User Management
- **Registration**: User signup with email verification
- **Profile Management**: User profile updates, password changes
- **Role Assignment**: Dynamic role and permission management
- **Account Lifecycle**: Account activation, suspension, deletion

### Security Architecture

#### Authentication Flow
1. **Login Request**: User credentials validation
2. **2FA Verification**: Optional second factor check
3. **Token Generation**: JWT creation with user claims
4. **Token Distribution**: Secure token delivery to client
5. **Session Creation**: Redis session establishment

#### Authorization Flow
1. **Request Interception**: Middleware captures requests
2. **Token Extraction**: JWT token from Authorization header
3. **Token Validation**: Signature and expiry verification
4. **Claims Processing**: User permissions extraction
5. **Access Decision**: Allow/deny based on resource requirements

### Database Schema
```sql
users (id, username, email, password_hash, created_at, is_active, role)
user_sessions (session_id, user_id, created_at, expires_at, ip_address)
api_keys (key_id, user_id, key_hash, permissions, created_at, last_used)
two_factor (user_id, secret_key, backup_codes, enabled, verified_at)
audit_log (id, user_id, action, ip_address, timestamp, details)
```

### API Endpoints

#### Core Authentication
- `POST /auth/login` - User login with credentials
- `POST /auth/logout` - Session termination
- `POST /auth/refresh` - Token refresh
- `GET /auth/profile` - User profile retrieval
- `PUT /auth/profile` - Profile updates

#### Two-Factor Authentication
- `POST /auth/2fa/setup` - 2FA initialization
- `POST /auth/2fa/verify` - TOTP verification
- `POST /auth/2fa/disable` - 2FA removal

#### API Key Management
- `POST /auth/keys` - API key creation
- `GET /auth/keys` - List user API keys
- `DELETE /auth/keys/{key_id}` - Key revocation

#### Administrative
- `GET /auth/users` - User listing (admin only)
- `POST /auth/users` - User creation
- `PUT /auth/users/{user_id}/role` - Role assignment

### Integration Patterns

#### Service Integration
All ActiveLog services integrate authentication via:
1. **Middleware Import**: Shared authentication middleware
2. **Token Validation**: Automatic request validation
3. **User Context**: Request context populated with user info
4. **Permission Checks**: Route-level permission enforcement

#### Frontend Integration
React applications integrate via:
1. **Login Components**: Reusable authentication UI
2. **Token Storage**: Secure token management in localStorage
3. **Automatic Refresh**: Background token refresh handling
4. **Route Protection**: Protected route components

### Security Features

#### Threat Protection
- **Rate Limiting**: Login attempt throttling
- **IP Blocking**: Automated IP-based blocking
- **Audit Logging**: Comprehensive security event logging
- **Anomaly Detection**: Unusual access pattern identification

#### Data Protection
- **Password Hashing**: bcrypt with configurable rounds
- **Token Encryption**: JWT signing with RS256
- **Session Security**: Secure cookie configuration
- **Data Encryption**: Sensitive data encryption at rest

### Configuration
```python
# Key configuration settings
JWT_SECRET_KEY: str  # JWT signing key
JWT_EXPIRY_HOURS: int = 24  # Token expiry time
ENABLE_2FA: bool = True  # Two-factor authentication
SESSION_TIMEOUT: int = 3600  # Session timeout (seconds)
MAX_LOGIN_ATTEMPTS: int = 5  # Rate limiting threshold
BCRYPT_ROUNDS: int = 12  # Password hashing complexity
```

### Performance Considerations
- **Redis Caching**: Session and token blacklist caching
- **Connection Pooling**: Database connection optimization
- **Async Operations**: Non-blocking authentication flows
- **Token Validation**: Optimized JWT verification

## Related Concepts
- **SEC-001**: Security architecture patterns
- **SEC-002**: Security middleware implementation
- **API-001**: API design patterns
- **DB-001**: Database architecture
- **CACHE-001**: Redis caching strategies

## Code References
- Service: `~/activelog/services/auth/`
- Main module: `~/activelog/services/auth/main.py`
- Models: `~/activelog/services/auth/models.py`
- Routes: `~/activelog/services/auth/routes.py`
- Middleware: `~/activelog/services/auth/middleware.py`

## Recent Changes
- Added enhanced 2FA support with backup codes
- Implemented threat assessment integration
- Added API key scoping and rotation
- Enhanced audit logging capabilities