# API Design: RESTful Architecture & Authentication

## Executive Summary

This document provides comprehensive API design for the compute marketplace platform, including RESTful architecture, authentication mechanisms (JWT, OAuth2), major endpoints with examples, rate limiting, and OpenAPI/Swagger specifications.

**API Version**: v1
**Base URL**: `https://api.marketplace.example.com/api/v1`
**Authentication**: JWT (primary), OAuth2 (social login)

---

## Table of Contents

1. [API Architecture Principles](#api-architecture-principles)
2. [Authentication & Authorization](#authentication--authorization)
3. [Core API Endpoints](#core-api-endpoints)
4. [Rate Limiting](#rate-limiting)
5. [Error Handling](#error-handling)
6. [Pagination & Filtering](#pagination--filtering)
7. [Webhooks](#webhooks)
8. [OpenAPI Specification](#openapi-specification)

---

## API Architecture Principles

### RESTful Design Principles

```
1. Resource-Based URLs
   ✓ Use nouns, not verbs: /users, /resources, /bookings
   ✗ Avoid: /getUser, /createResource

2. HTTP Methods
   GET    - Retrieve resource(s)
   POST   - Create new resource
   PUT    - Replace entire resource
   PATCH  - Update specific fields
   DELETE - Remove resource

3. Status Codes
   200 OK              - Success (GET, PATCH, PUT)
   201 Created         - Success (POST)
   204 No Content      - Success (DELETE)
   400 Bad Request     - Invalid input
   401 Unauthorized    - Missing/invalid auth
   403 Forbidden       - Insufficient permissions
   404 Not Found       - Resource doesn't exist
   409 Conflict        - Resource conflict (duplicate)
   422 Unprocessable   - Validation error
   429 Too Many Requests - Rate limit exceeded
   500 Internal Error  - Server error

4. Versioning
   URL versioning: /api/v1/resources (recommended)
   Header versioning: Accept: application/vnd.api.v1+json

5. HATEOAS (Hypermedia)
   Include links to related resources in responses

6. Idempotency
   GET, PUT, DELETE - Idempotent
   POST - Not idempotent (use idempotency keys for safety)
```

### API Structure

```
/api/v1/
├── /auth
│   ├── POST   /register
│   ├── POST   /login
│   ├── POST   /refresh
│   ├── POST   /logout
│   ├── POST   /forgot-password
│   └── POST   /reset-password
│
├── /users
│   ├── GET    /users                    (admin)
│   ├── GET    /users/:id
│   ├── GET    /users/me
│   ├── PATCH  /users/:id
│   ├── DELETE /users/:id
│   └── GET    /users/:id/reviews
│
├── /resources
│   ├── GET    /resources
│   ├── POST   /resources
│   ├── GET    /resources/:id
│   ├── PATCH  /resources/:id
│   ├── DELETE /resources/:id
│   ├── GET    /resources/:id/availability
│   └── GET    /resources/:id/reviews
│
├── /bookings
│   ├── GET    /bookings
│   ├── POST   /bookings
│   ├── GET    /bookings/:id
│   ├── PATCH  /bookings/:id
│   ├── DELETE /bookings/:id (cancel)
│   └── POST   /bookings/:id/extend
│
├── /payments
│   ├── GET    /payments
│   ├── GET    /payments/:id
│   ├── POST   /payments/create-intent
│   └── POST   /payments/:id/refund
│
├── /reviews
│   ├── GET    /reviews
│   ├── POST   /reviews
│   ├── GET    /reviews/:id
│   ├── PATCH  /reviews/:id
│   └── DELETE /reviews/:id
│
├── /messages
│   ├── GET    /messages/conversations
│   ├── GET    /messages/conversations/:id
│   ├── POST   /messages/conversations/:id/messages
│   ├── PATCH  /messages/:id/read
│   └── DELETE /messages/:id
│
├── /notifications
│   ├── GET    /notifications
│   ├── PATCH  /notifications/:id/read
│   ├── POST   /notifications/mark-all-read
│   └── DELETE /notifications/:id
│
├── /analytics
│   ├── GET    /analytics/dashboard
│   ├── GET    /analytics/revenue
│   └── GET    /analytics/usage
│
└── /pricing
    └── POST   /pricing/calculate
```

---

## Authentication & Authorization

### JWT (JSON Web Token) - Primary Method

#### How JWT Works

```
┌─────────────────────────────────────────────────────────┐
│  1. User Login                                          │
│  POST /api/v1/auth/login                                │
│  { email: "user@example.com", password: "..." }        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  2. Server Validates Credentials                        │
│  - Check email exists                                   │
│  - Verify password hash (bcrypt)                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  3. Server Generates JWT                                │
│  Payload: { userId, email, role }                       │
│  Sign with secret key                                   │
│  Set expiration (15 minutes)                            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  4. Client Receives Token                               │
│  {                                                      │
│    "access_token": "eyJhbGc...",                        │
│    "refresh_token": "dGhpc2lz...",                      │
│    "expires_in": 900                                    │
│  }                                                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  5. Client Stores Token (localStorage/cookie)           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  6. Client Includes Token in Requests                   │
│  Authorization: Bearer eyJhbGc...                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  7. Server Verifies Token                               │
│  - Verify signature                                     │
│  - Check expiration                                     │
│  - Extract user info from payload                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  8. Server Processes Request                            │
│  - Access user data from token                          │
│  - Apply role-based permissions                         │
└─────────────────────────────────────────────────────────┘
```

#### JWT Implementation (Node.js)

**1. Login Endpoint**

```typescript
// auth.controller.ts
import { Controller, Post, Body, UnauthorizedException } from '@nestjs/common';
import { AuthService } from './auth.service';

class LoginDto {
  email: string;
  password: string;
}

@Controller('api/v1/auth')
export class AuthController {
  constructor(private authService: AuthService) {}

  @Post('login')
  async login(@Body() loginDto: LoginDto) {
    const user = await this.authService.validateUser(
      loginDto.email,
      loginDto.password
    );

    if (!user) {
      throw new UnauthorizedException('Invalid credentials');
    }

    return this.authService.login(user);
  }
}
```

**2. Auth Service (Token Generation)**

```typescript
// auth.service.ts
import { Injectable } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import * as bcrypt from 'bcrypt';

@Injectable()
export class AuthService {
  constructor(
    private jwtService: JwtService,
    private usersService: UsersService,
  ) {}

  async validateUser(email: string, password: string) {
    const user = await this.usersService.findByEmail(email);

    if (!user) {
      return null;
    }

    const isPasswordValid = await bcrypt.compare(password, user.passwordHash);

    if (!isPasswordValid) {
      return null;
    }

    return user;
  }

  async login(user: any) {
    const payload = {
      sub: user.id,
      email: user.email,
      role: user.role,
    };

    const accessToken = this.jwtService.sign(payload, {
      expiresIn: '15m', // Short-lived access token
    });

    const refreshToken = this.jwtService.sign(payload, {
      expiresIn: '7d', // Long-lived refresh token
    });

    // Store refresh token in database (for revocation)
    await this.storeRefreshToken(user.id, refreshToken);

    return {
      access_token: accessToken,
      refresh_token: refreshToken,
      expires_in: 900, // 15 minutes in seconds
      token_type: 'Bearer',
      user: {
        id: user.id,
        email: user.email,
        firstName: user.firstName,
        lastName: user.lastName,
        role: user.role,
      },
    };
  }

  async storeRefreshToken(userId: string, token: string) {
    // Hash token before storing
    const hashedToken = await bcrypt.hash(token, 10);

    await this.db.query(
      'INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES ($1, $2, $3)',
      [userId, hashedToken, new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)]
    );
  }
}
```

**3. JWT Strategy (Token Verification)**

```typescript
// jwt.strategy.ts
import { Injectable, UnauthorizedException } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor(private usersService: UsersService) {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: process.env.JWT_SECRET,
    });
  }

  async validate(payload: any) {
    // Payload from JWT: { sub, email, role }
    const user = await this.usersService.findOne(payload.sub);

    if (!user || !user.isActive) {
      throw new UnauthorizedException();
    }

    // This will be attached to request.user
    return {
      id: payload.sub,
      email: payload.email,
      role: payload.role,
    };
  }
}
```

**4. JWT Guard (Protect Routes)**

```typescript
// jwt-auth.guard.ts
import { Injectable, ExecutionContext } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';

@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {
  canActivate(context: ExecutionContext) {
    return super.canActivate(context);
  }
}

// Usage in controllers
@Controller('api/v1/resources')
export class ResourcesController {
  @Get()
  @UseGuards(JwtAuthGuard) // Require authentication
  async findAll(@Request() req) {
    console.log('User:', req.user); // { id, email, role }
    return this.resourcesService.findAll();
  }
}
```

**5. Role-Based Access Control (RBAC)**

```typescript
// roles.decorator.ts
import { SetMetadata } from '@nestjs/common';

export const ROLES_KEY = 'roles';
export const Roles = (...roles: string[]) => SetMetadata(ROLES_KEY, roles);

// roles.guard.ts
import { Injectable, CanActivate, ExecutionContext } from '@nestjs/common';
import { Reflector } from '@nestjs/core';

@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const requiredRoles = this.reflector.getAllAndOverride<string[]>(ROLES_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);

    if (!requiredRoles) {
      return true; // No roles required
    }

    const { user } = context.switchToHttp().getRequest();
    return requiredRoles.some((role) => user.role === role);
  }
}

// Usage in controllers
@Delete(':id')
@UseGuards(JwtAuthGuard, RolesGuard)
@Roles('admin') // Only admins can delete
async remove(@Param('id') id: string) {
  return this.usersService.remove(id);
}
```

**6. Refresh Token Endpoint**

```typescript
@Post('refresh')
async refresh(@Body() dto: { refreshToken: string }) {
  try {
    // Verify refresh token
    const payload = this.jwtService.verify(dto.refreshToken);

    // Check if refresh token exists in database (not revoked)
    const isValid = await this.validateRefreshToken(payload.sub, dto.refreshToken);

    if (!isValid) {
      throw new UnauthorizedException('Invalid refresh token');
    }

    // Generate new access token
    const accessToken = this.jwtService.sign({
      sub: payload.sub,
      email: payload.email,
      role: payload.role,
    }, { expiresIn: '15m' });

    return {
      access_token: accessToken,
      expires_in: 900,
    };
  } catch (error) {
    throw new UnauthorizedException('Invalid refresh token');
  }
}
```

### OAuth2 (Social Login)

#### OAuth2 Flow (Google Example)

```
┌─────────────────────────────────────────────────────────┐
│  1. User Clicks "Login with Google"                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  2. Redirect to Google OAuth                            │
│  https://accounts.google.com/o/oauth2/v2/auth           │
│  ?client_id=...&redirect_uri=...&scope=...              │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  3. User Authorizes on Google                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  4. Google Redirects with Code                          │
│  https://api.marketplace.com/auth/google/callback       │
│  ?code=...&state=...                                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  5. Server Exchanges Code for Access Token              │
│  POST https://oauth2.googleapis.com/token               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  6. Server Fetches User Profile from Google             │
│  GET https://www.googleapis.com/oauth2/v2/userinfo      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  7. Server Creates/Updates User in Database             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  8. Server Generates JWT for User                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  9. Redirect to Frontend with JWT                       │
│  https://marketplace.com/auth/callback?token=...        │
└─────────────────────────────────────────────────────────┘
```

#### OAuth2 Implementation (Passport.js)

```typescript
// google.strategy.ts
import { Injectable } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { Strategy, VerifyCallback } from 'passport-google-oauth20';

@Injectable()
export class GoogleStrategy extends PassportStrategy(Strategy, 'google') {
  constructor(private authService: AuthService) {
    super({
      clientID: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
      callbackURL: process.env.GOOGLE_CALLBACK_URL,
      scope: ['email', 'profile'],
    });
  }

  async validate(
    accessToken: string,
    refreshToken: string,
    profile: any,
    done: VerifyCallback,
  ): Promise<any> {
    const { name, emails, photos } = profile;

    const user = await this.authService.findOrCreateOAuthUser({
      email: emails[0].value,
      firstName: name.givenName,
      lastName: name.familyName,
      avatar: photos[0].value,
      provider: 'google',
      providerId: profile.id,
    });

    done(null, user);
  }
}

// auth.controller.ts
@Get('google')
@UseGuards(AuthGuard('google'))
async googleAuth() {
  // Initiates OAuth flow
}

@Get('google/callback')
@UseGuards(AuthGuard('google'))
async googleAuthCallback(@Req() req, @Res() res) {
  // User is now in req.user
  const jwt = await this.authService.login(req.user);

  // Redirect to frontend with token
  res.redirect(`${process.env.FRONTEND_URL}/auth/callback?token=${jwt.access_token}`);
}
```

---

## Core API Endpoints

### 1. Authentication Endpoints

#### POST /api/v1/auth/register

**Description**: Register a new user

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "firstName": "John",
  "lastName": "Doe",
  "role": "buyer"
}
```

**Response (201 Created)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "dGhpc2lz...",
  "expires_in": 900,
  "token_type": "Bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "firstName": "John",
    "lastName": "Doe",
    "role": "buyer",
    "createdAt": "2025-10-14T10:30:00Z"
  }
}
```

**Errors**:
- `400` - Invalid input (email format, weak password)
- `409` - User already exists

---

#### POST /api/v1/auth/login

**Description**: Login with email and password

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response (200 OK)**: Same as register

**Errors**:
- `401` - Invalid credentials
- `400` - Missing fields

---

### 2. User Endpoints

#### GET /api/v1/users/me

**Description**: Get current user's profile

**Headers**:
```
Authorization: Bearer eyJhbGc...
```

**Response (200 OK)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "firstName": "John",
  "lastName": "Doe",
  "displayName": "John Doe",
  "role": "buyer",
  "avatarUrl": "https://cdn.example.com/avatars/user.jpg",
  "bio": "Software developer interested in AI/ML",
  "rating": {
    "average": 4.8,
    "count": 42
  },
  "totalBookings": 67,
  "createdAt": "2025-01-15T10:30:00Z",
  "lastLoginAt": "2025-10-14T08:00:00Z"
}
```

---

#### PATCH /api/v1/users/me

**Description**: Update current user's profile

**Request Body**:
```json
{
  "firstName": "Jane",
  "lastName": "Smith",
  "bio": "Updated bio",
  "avatarUrl": "https://cdn.example.com/avatars/new.jpg"
}
```

**Response (200 OK)**: Updated user object

---

### 3. Resource Endpoints

#### GET /api/v1/resources

**Description**: Search and filter resources

**Query Parameters**:
```
?type=gpu                    // Filter by type
&minPrice=5                  // Minimum price
&maxPrice=50                 // Maximum price
&location=us-east-1          // Filter by location
&availability=available      // Only available
&gpuModel=RTX 4090          // Filter by GPU model
&minRam=32                   // Minimum RAM (GB)
&page=1                      // Pagination
&limit=20                    // Results per page
&sort=price:asc              // Sort by price ascending
&search=machine learning     // Full-text search
```

**Response (200 OK)**:
```json
{
  "data": [
    {
      "id": "res-123",
      "name": "High-Performance GPU Server",
      "description": "NVIDIA RTX 4090 with 128GB RAM",
      "resourceType": "gpu",
      "specs": {
        "cpu": {
          "cores": 32,
          "model": "AMD EPYC 7763",
          "frequencyGhz": 3.5
        },
        "ram": {
          "sizeGb": 128,
          "type": "DDR4"
        },
        "gpu": [
          {
            "model": "NVIDIA RTX 4090",
            "vramGb": 24,
            "count": 2
          }
        ],
        "storage": {
          "type": "NVMe",
          "sizeTb": 2
        }
      },
      "pricePerHour": 12.50,
      "currency": "USD",
      "availabilityStatus": "available",
      "location": {
        "region": "us-east-1",
        "city": "New York",
        "country": "US"
      },
      "rating": {
        "average": 4.9,
        "count": 156
      },
      "provider": {
        "id": "provider-456",
        "displayName": "TechCloud Solutions",
        "rating": 4.8
      },
      "createdAt": "2025-01-10T10:00:00Z"
    }
    // ... more resources
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 458,
    "totalPages": 23
  }
}
```

---

#### POST /api/v1/resources

**Description**: Create a new resource (providers only)

**Headers**:
```
Authorization: Bearer eyJhbGc...
```

**Request Body**:
```json
{
  "name": "GPU Server for ML Training",
  "description": "Powerful GPU server optimized for deep learning",
  "resourceType": "gpu",
  "specs": {
    "cpu": {
      "cores": 32,
      "model": "AMD EPYC 7763"
    },
    "ram": {
      "sizeGb": 128,
      "type": "DDR4"
    },
    "gpu": [
      {
        "model": "NVIDIA RTX 4090",
        "vramGb": 24,
        "count": 2
      }
    ]
  },
  "pricePerHour": 12.50,
  "location": {
    "region": "us-east-1",
    "city": "New York",
    "country": "US"
  }
}
```

**Response (201 Created)**: Resource object

**Errors**:
- `403` - Not authorized (not a provider)
- `422` - Validation error

---

#### GET /api/v1/resources/:id/availability

**Description**: Check resource availability for a time range

**Query Parameters**:
```
?startTime=2025-02-01T10:00:00Z
&endTime=2025-02-01T14:00:00Z
```

**Response (200 OK)**:
```json
{
  "resourceId": "res-123",
  "isAvailable": true,
  "conflicts": [],
  "nextAvailableSlot": null
}
```

Or if not available:
```json
{
  "resourceId": "res-123",
  "isAvailable": false,
  "conflicts": [
    {
      "startTime": "2025-02-01T09:00:00Z",
      "endTime": "2025-02-01T13:00:00Z",
      "bookingId": "booking-789"
    }
  ],
  "nextAvailableSlot": {
    "startTime": "2025-02-01T13:00:00Z"
  }
}
```

---

### 4. Booking Endpoints

#### POST /api/v1/bookings

**Description**: Create a new booking

**Request Body**:
```json
{
  "resourceId": "res-123",
  "startTime": "2025-02-01T10:00:00Z",
  "endTime": "2025-02-01T14:00:00Z",
  "paymentMethod": "credit_card"
}
```

**Response (201 Created)**:
```json
{
  "id": "booking-789",
  "userId": "user-456",
  "resourceId": "res-123",
  "startTime": "2025-02-01T10:00:00Z",
  "endTime": "2025-02-01T14:00:00Z",
  "duration": 4,
  "pricePerHour": 12.50,
  "totalCost": 50.00,
  "currency": "USD",
  "status": "pending",
  "payment": {
    "id": "payment-321",
    "status": "pending",
    "clientSecret": "pi_abc123_secret_xyz789" // For Stripe
  },
  "createdAt": "2025-10-14T10:30:00Z"
}
```

**Errors**:
- `400` - Invalid time range
- `409` - Resource not available
- `422` - Validation error

---

#### GET /api/v1/bookings

**Description**: Get user's bookings

**Query Parameters**:
```
?status=active              // Filter by status
&startDate=2025-02-01       // Filter by date range
&endDate=2025-02-28
&page=1
&limit=20
```

**Response (200 OK)**:
```json
{
  "data": [
    {
      "id": "booking-789",
      "resource": {
        "id": "res-123",
        "name": "GPU Server",
        "specs": { /* ... */ }
      },
      "startTime": "2025-02-01T10:00:00Z",
      "endTime": "2025-02-01T14:00:00Z",
      "totalCost": 50.00,
      "status": "active",
      "createdAt": "2025-01-20T10:30:00Z"
    }
  ],
  "pagination": { /* ... */ }
}
```

---

#### PATCH /api/v1/bookings/:id

**Description**: Update booking (cancel, extend, etc.)

**Request Body (Cancel)**:
```json
{
  "status": "cancelled",
  "cancellationReason": "Change of plans"
}
```

**Request Body (Extend)**:
```json
{
  "newEndTime": "2025-02-01T18:00:00Z"
}
```

---

### 5. Payment Endpoints

#### POST /api/v1/payments/create-intent

**Description**: Create payment intent (for Stripe)

**Request Body**:
```json
{
  "bookingId": "booking-789",
  "paymentMethod": "credit_card"
}
```

**Response (200 OK)**:
```json
{
  "paymentId": "payment-321",
  "clientSecret": "pi_abc123_secret_xyz789",
  "amount": 50.00,
  "currency": "USD"
}
```

---

### 6. Pricing Endpoint

#### POST /api/v1/pricing/calculate

**Description**: Calculate dynamic price for a booking

**Request Body**:
```json
{
  "resourceId": "res-123",
  "startTime": "2025-02-01T10:00:00Z",
  "duration": 4
}
```

**Response (200 OK)**:
```json
{
  "basePrice": 10.00,
  "adjustedPrice": 11.50,
  "totalCost": 46.00,
  "factors": {
    "demand": 1.2,
    "supply": 0.95,
    "time": 1.05,
    "reputation": 1.1,
    "duration": 0.95,
    "seasonal": 1.0
  },
  "breakdown": [
    "Base price: $10.00/hour",
    "Demand factor: 1.20x (+20%)",
    "Supply factor: 0.95x (-5%)",
    "Time factor: 1.05x (+5%)",
    "Reputation factor: 1.10x (+10%)",
    "Duration factor: 0.95x (-5%)",
    "Adjusted price: $11.50/hour",
    "Total cost (4h): $46.00"
  ]
}
```

---

## Rate Limiting

### Strategy

```
Tier 1: Unauthenticated Users
  - 100 requests per 15 minutes per IP
  - Applies to: /auth/login, /auth/register, /resources (public)

Tier 2: Authenticated Users (Free)
  - 1,000 requests per hour per user
  - Applies to: All authenticated endpoints

Tier 3: Premium Users
  - 10,000 requests per hour per user

Tier 4: API Keys (for integrations)
  - Custom limits based on plan
```

### Implementation (Express + Redis)

```javascript
// rate-limiter.middleware.js
const Redis = require('ioredis');
const redis = new Redis();

async function rateLimiter(req, res, next) {
  const key = req.user ? `rate:user:${req.user.id}` : `rate:ip:${req.ip}`;
  const limit = req.user ? 1000 : 100;
  const window = req.user ? 3600 : 900; // 1 hour vs 15 min

  try {
    const current = await redis.incr(key);

    if (current === 1) {
      await redis.expire(key, window);
    }

    const ttl = await redis.ttl(key);

    // Set rate limit headers
    res.setHeader('X-RateLimit-Limit', limit);
    res.setHeader('X-RateLimit-Remaining', Math.max(0, limit - current));
    res.setHeader('X-RateLimit-Reset', Date.now() + (ttl * 1000));

    if (current > limit) {
      return res.status(429).json({
        error: 'Too Many Requests',
        message: 'Rate limit exceeded. Please try again later.',
        retryAfter: ttl,
      });
    }

    next();
  } catch (error) {
    console.error('Rate limiter error:', error);
    next(); // Fail open (don't block requests on Redis failure)
  }
}

module.exports = rateLimiter;
```

---

## Error Handling

### Standard Error Response

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Resource with ID 'res-123' not found",
    "statusCode": 404,
    "timestamp": "2025-10-14T10:30:00Z",
    "path": "/api/v1/resources/res-123",
    "requestId": "req-abc123"
  }
}
```

### Error Codes

```typescript
enum ErrorCode {
  // Authentication (401)
  INVALID_CREDENTIALS = 'INVALID_CREDENTIALS',
  TOKEN_EXPIRED = 'TOKEN_EXPIRED',
  INVALID_TOKEN = 'INVALID_TOKEN',

  // Authorization (403)
  FORBIDDEN = 'FORBIDDEN',
  INSUFFICIENT_PERMISSIONS = 'INSUFFICIENT_PERMISSIONS',

  // Not Found (404)
  RESOURCE_NOT_FOUND = 'RESOURCE_NOT_FOUND',
  USER_NOT_FOUND = 'USER_NOT_FOUND',

  // Validation (422)
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  INVALID_INPUT = 'INVALID_INPUT',

  // Conflict (409)
  RESOURCE_ALREADY_EXISTS = 'RESOURCE_ALREADY_EXISTS',
  BOOKING_CONFLICT = 'BOOKING_CONFLICT',

  // Rate Limiting (429)
  RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED',

  // Server Error (500)
  INTERNAL_SERVER_ERROR = 'INTERNAL_SERVER_ERROR',
}
```

### Global Error Handler (NestJS)

```typescript
// http-exception.filter.ts
import { ExceptionFilter, Catch, ArgumentsHost, HttpException } from '@nestjs/common';

@Catch(HttpException)
export class HttpExceptionFilter implements ExceptionFilter {
  catch(exception: HttpException, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse();
    const request = ctx.getRequest();
    const status = exception.getStatus();
    const exceptionResponse: any = exception.getResponse();

    response.status(status).json({
      error: {
        code: exceptionResponse.code || 'UNKNOWN_ERROR',
        message: exceptionResponse.message || exception.message,
        statusCode: status,
        timestamp: new Date().toISOString(),
        path: request.url,
        requestId: request.headers['x-request-id'],
      },
    });
  }
}
```

---

## Pagination & Filtering

### Query Parameters

```
?page=1                     // Page number (1-indexed)
&limit=20                   // Results per page (default: 20, max: 100)
&sort=createdAt:desc        // Sort by field:direction
&filter[status]=active      // Filter by field
&search=keyword             // Full-text search
```

### Response Format

```json
{
  "data": [ /* ... */ ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 458,
    "totalPages": 23,
    "hasNextPage": true,
    "hasPrevPage": false
  },
  "links": {
    "self": "/api/v1/resources?page=1&limit=20",
    "first": "/api/v1/resources?page=1&limit=20",
    "last": "/api/v1/resources?page=23&limit=20",
    "next": "/api/v1/resources?page=2&limit=20",
    "prev": null
  }
}
```

---

## Webhooks

### Events

```
booking.created
booking.confirmed
booking.completed
booking.cancelled
payment.succeeded
payment.failed
resource.created
resource.updated
```

### Webhook Payload

```json
{
  "id": "evt_abc123",
  "type": "booking.completed",
  "createdAt": "2025-10-14T10:30:00Z",
  "data": {
    "id": "booking-789",
    "userId": "user-456",
    "resourceId": "res-123",
    "status": "completed",
    "totalCost": 50.00
  }
}
```

### Webhook Signature Verification

```javascript
const crypto = require('crypto');

function verifyWebhookSignature(payload, signature, secret) {
  const hmac = crypto.createHmac('sha256', secret);
  const digest = hmac.update(JSON.stringify(payload)).digest('hex');

  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(digest)
  );
}

// Usage
app.post('/webhooks', (req, res) => {
  const signature = req.headers['x-webhook-signature'];

  if (!verifyWebhookSignature(req.body, signature, WEBHOOK_SECRET)) {
    return res.status(401).json({ error: 'Invalid signature' });
  }

  // Process webhook
  handleWebhook(req.body);

  res.status(200).json({ received: true });
});
```

---

## OpenAPI Specification

### Swagger/OpenAPI Setup (NestJS)

```typescript
// main.ts
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';

const config = new DocumentBuilder()
  .setTitle('Compute Marketplace API')
  .setDescription('RESTful API for compute resource marketplace')
  .setVersion('1.0')
  .addBearerAuth()
  .addTag('auth', 'Authentication endpoints')
  .addTag('users', 'User management')
  .addTag('resources', 'Resource management')
  .addTag('bookings', 'Booking management')
  .addTag('payments', 'Payment processing')
  .build();

const document = SwaggerModule.createDocument(app, config);
SwaggerModule.setup('api/docs', app, document);

// Available at: http://localhost:3000/api/docs
```

### OpenAPI YAML Example

```yaml
openapi: 3.0.0
info:
  title: Compute Marketplace API
  version: 1.0.0
  description: RESTful API for compute resource marketplace

servers:
  - url: https://api.marketplace.example.com/api/v1
    description: Production
  - url: https://api-staging.marketplace.example.com/api/v1
    description: Staging

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  schemas:
    Resource:
      type: object
      properties:
        id:
          type: string
          format: uuid
        name:
          type: string
        pricePerHour:
          type: number
          format: decimal
        availabilityStatus:
          type: string
          enum: [available, in_use, maintenance, offline]

paths:
  /resources:
    get:
      tags:
        - resources
      summary: List all resources
      parameters:
        - in: query
          name: page
          schema:
            type: integer
        - in: query
          name: limit
          schema:
            type: integer
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Resource'

    post:
      tags:
        - resources
      summary: Create a new resource
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Resource'
      responses:
        '201':
          description: Resource created
```

---

## Conclusion

This API design provides:

1. **RESTful architecture** following industry best practices
2. **Secure authentication** with JWT and OAuth2 support
3. **Role-based access control** for fine-grained permissions
4. **Comprehensive endpoints** covering all marketplace operations
5. **Rate limiting** to prevent abuse
6. **Standardized error handling** for consistent client experience
7. **Pagination and filtering** for efficient data retrieval
8. **Webhooks** for real-time event notifications
9. **OpenAPI documentation** for easy integration

**Next Steps**:
1. Implement API versioning strategy
2. Add GraphQL endpoint (optional)
3. Implement WebSocket support for real-time features
4. Set up API monitoring and analytics
5. Create client SDKs (JavaScript, Python)

---

**Document Version**: 1.0
**Last Updated**: 2025-10-14
**Author**: API Architecture Team
