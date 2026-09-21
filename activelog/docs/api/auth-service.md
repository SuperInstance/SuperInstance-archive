# Auth Service API

The Auth Service handles authentication, authorization, and user management for ActiveLog.

## Base URL
```
http://localhost:8001
```

## Endpoints

### Authentication

#### POST /auth/login
Authenticate user and return JWT token.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "jwt_token_string",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_token_string",
  "user": {
    "id": "user_id",
    "username": "username",
    "email": "user@example.com",
    "roles": ["user", "admin"]
  }
}
```

#### POST /auth/register
Register a new user account.

**Request Body:**
```json
{
  "username": "string",
  "email": "user@example.com",
  "password": "string",
  "full_name": "User Full Name"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": "user_id",
    "username": "username",
    "email": "user@example.com"
  }
}
```

#### POST /auth/refresh
Refresh an access token using a refresh token.

**Request Body:**
```json
{
  "refresh_token": "refresh_token_string"
}
```

**Response:**
```json
{
  "access_token": "new_jwt_token",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### POST /auth/logout
Invalidate user session and tokens.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "message": "Successfully logged out"
}
```

### User Management

#### GET /auth/me
Get current user information.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "id": "user_id",
  "username": "username",
  "email": "user@example.com",
  "full_name": "User Full Name",
  "roles": ["user"],
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-01T12:00:00Z",
  "is_active": true,
  "preferences": {
    "theme": "dark",
    "language": "en"
  }
}
```

#### PUT /auth/me
Update current user information.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "full_name": "Updated Name",
  "email": "newemail@example.com",
  "preferences": {
    "theme": "light",
    "language": "es"
  }
}
```

**Response:**
```json
{
  "message": "Profile updated successfully",
  "user": {
    "id": "user_id",
    "username": "username",
    "email": "newemail@example.com",
    "full_name": "Updated Name"
  }
}
```

#### POST /auth/change-password
Change user password.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "current_password": "old_password",
  "new_password": "new_password",
  "confirm_password": "new_password"
}
```

**Response:**
```json
{
  "message": "Password changed successfully"
}
```

### Password Reset

#### POST /auth/forgot-password
Request password reset email.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "Password reset email sent"
}
```

#### POST /auth/reset-password
Reset password using reset token.

**Request Body:**
```json
{
  "reset_token": "reset_token_from_email",
  "new_password": "new_password",
  "confirm_password": "new_password"
}
```

**Response:**
```json
{
  "message": "Password reset successfully"
}
```

### Role Management

#### GET /auth/users
List all users (admin only).

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20)
- `search`: Search term
- `role`: Filter by role

**Response:**
```json
{
  "users": [
    {
      "id": "user_id",
      "username": "username",
      "email": "user@example.com",
      "full_name": "User Name",
      "roles": ["user"],
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

#### PUT /auth/users/{user_id}/roles
Update user roles (admin only).

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Request Body:**
```json
{
  "roles": ["user", "moderator"]
}
```

**Response:**
```json
{
  "message": "User roles updated successfully",
  "user": {
    "id": "user_id",
    "username": "username",
    "roles": ["user", "moderator"]
  }
}
```

### Two-Factor Authentication

#### POST /auth/2fa/enable
Enable 2FA for current user.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "qr_code": "data:image/png;base64,...",
  "secret": "JBSWY3DPEHPK3PXP",
  "backup_codes": [
    "12345678",
    "87654321"
  ]
}
```

#### POST /auth/2fa/verify
Verify 2FA setup with TOTP code.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "totp_code": "123456"
}
```

**Response:**
```json
{
  "message": "2FA enabled successfully"
}
```

#### POST /auth/2fa/disable
Disable 2FA for current user.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "password": "current_password",
  "totp_code": "123456"
}
```

**Response:**
```json
{
  "message": "2FA disabled successfully"
}
```

## Error Codes

| Code | Status | Description |
|------|--------|-------------|
| AUTH001 | 401 | Invalid credentials |
| AUTH002 | 401 | Token expired |
| AUTH003 | 401 | Invalid token |
| AUTH004 | 403 | Insufficient permissions |
| AUTH005 | 409 | Username already exists |
| AUTH006 | 409 | Email already exists |
| AUTH007 | 400 | Invalid password format |
| AUTH008 | 400 | Invalid email format |
| AUTH009 | 429 | Too many login attempts |
| AUTH010 | 400 | Invalid 2FA code |

## Rate Limits

- Login attempts: 5 per minute per IP
- Registration: 3 per minute per IP
- Password reset: 1 per minute per email
- General API calls: 100 per minute per user

## Security Features

- JWT tokens with configurable expiration
- Refresh tokens for session management
- Password strength validation
- Account lockout after failed attempts
- Two-factor authentication (TOTP)
- Session management and invalidation
- Rate limiting and abuse protection
- Password reset with secure tokens
- Audit logging for all auth events

## Examples

### Login Example
```bash
curl -X POST "http://localhost:8001/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "securepassword"
  }'
```

### Access Protected Endpoint
```bash
curl -X GET "http://localhost:8001/protected" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

### Register New User
```bash
curl -X POST "http://localhost:8001/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "securepassword123",
    "full_name": "New User"
  }'
```