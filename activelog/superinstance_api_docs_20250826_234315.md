# SuperInstance.AI API Documentation

Comprehensive API documentation for the SuperInstance multi-domain AI platform

**Version:** 1.0.0  
**Generated:** 2025-08-26T23:43:15.711556

## Overview

SuperInstance.AI is a revolutionary multi-domain AI platform that provides specialized AI services for fitness, productivity, fishing, creative campaigns, and business analytics with cross-domain correlation intelligence.

## Services

### Authentication Service

JWT-based authentication and authorization service for all SuperInstance domains

**Base URL:** `http://localhost:8001`

#### Endpoints

##### POST /api/register

Register new user account

##### POST /api/login

Login user and get authentication tokens

##### POST /api/refresh

Refresh access token

##### POST /api/logout

Logout user (invalidate refresh tokens)

##### GET /api/me

Get current user profile

##### POST /api/grant-service/{service_name}

Grant current user access to a service

##### POST /api/validate-token

Validate JWT token (for other services)

##### GET /api/health

Health check endpoint

##### GET /api/metrics

Get service metrics

### API Gateway

Central routing and load balancing for all SuperInstance services

**Base URL:** `http://localhost:8088`

#### Endpoints

##### GET /

Gateway information endpoint

##### GET /health

Enhanced health check with service status

##### GET /metrics

Get gateway metrics (admin only)

##### POST /auth/validate

Validate JWT token and return user info

##### GET /services

List all available services with their status and endpoints

##### GET /docs

Custom documentation page with service discovery

##### GET /docs/swagger

Interactive Swagger UI documentation

##### GET /redoc

ReDoc documentation

##### POST /api/monitoring/logs

Receive monitoring logs from frontend

##### GET /api/monitoring/health

Get monitoring system health

##### GET /unified-docs

Test endpoint for unified documentation

##### GET /openapi.json

Enhanced unified OpenAPI schema with all service documentation

##### GET /api/{service}/docs

Proxy documentation from downstream services

##### GET /api/{service}/openapi.json

Proxy OpenAPI schema from downstream services

##### POST /cache/invalidate

Invalidate cache entries matching patterns (admin only)

##### GET /cache/stats

Get cache statistics (admin only)

##### PATCH /api/{service}/{path}

Enhanced proxy with caching, deduplication, and circuit breaker

##### DELETE /api/{service}/{path}

Enhanced proxy with caching, deduplication, and circuit breaker

##### POST /api/{service}/{path}

Enhanced proxy with caching, deduplication, and circuit breaker

##### GET /api/{service}/{path}

Enhanced proxy with caching, deduplication, and circuit breaker

##### PUT /api/{service}/{path}

Enhanced proxy with caching, deduplication, and circuit breaker

### User Management Service

User profiles, preferences, and cross-domain settings management

**Base URL:** `http://localhost:8092`

#### Endpoints

##### GET /health

Health Check

##### GET /users/profile

EDUCATIONAL: Comprehensive user profile retrieval with fitness context
INTEGRATION: Connects user data with AI insights and recommendations

##### PUT /users/profile

EDUCATIONAL: User profile updates with AI insights integration
INNOVATION: Triggers AI preference learning when profile changes

##### POST /users/preferences

BREAKTHROUGH FEATURE: Advanced preference management for AI personalization
EDUCATION: Demonstrates how user preferences drive AI recommendation quality

##### POST /users/goals

GOAL MANAGEMENT: Smart goal tracking with AI-powered progress monitoring
FUTURE INTEGRATION: Goals will drive workout recommendations

##### GET /users/goals

Get user goals with progress tracking

##### GET /users/dashboard

COMPREHENSIVE DASHBOARD: All user data with AI insights integration
MOBILE UI READY: Structured data for mobile interface consumption

### ActiveLog AI Service

Fitness and health AI insights with cross-domain correlations

**Base URL:** `http://localhost:8090`

#### Endpoints

##### GET /health

Health Check

##### POST /workout/insights

EDUCATIONAL: Generate AI-powered insights for a specific workout session
INTEGRATION: Connects workout data with user profile for personalized recommendations

##### POST /nutrition/insights

BREAKTHROUGH IMPLEMENTATION: Advanced nutrition analysis with AI-powered insights
INNOVATION: Cross-domain correlation with workout performance and goals

##### POST /workout/store-embedding

BREAKTHROUGH FEATURE: Store workout embeddings for future similarity search
EDUCATIONAL: Demonstrates embedding storage pipeline for AI recommendations

##### GET /user/{user_id}/fitness-trends

CROSS-DOMAIN CORRELATION: Analyze fitness trends with potential personal/business correlations
EDUCATIONAL: Demonstrates SuperInstance multi-domain architecture

### PersonalLog AI Service

Productivity optimization and habit formation AI

**Base URL:** `http://localhost:8095`

#### Endpoints

##### GET /health

Health Check

##### POST /productivity/insights

BREAKTHROUGH: Personal productivity insights with fitness correlation
SUPERINSTANCE INNOVATION: Cross-domain intelligence leveraging ActiveLog success

##### POST /productivity/goals

INNOVATION: Personal productivity goal tracking with AI optimization
COMPUTE CAPITAL: Goal achievement increases user's computational resource value

##### GET /productivity/dashboard

SUPERINSTANCE DASHBOARD: Personal productivity with cross-domain insights
MOBILE READY: Structured for revolutionary mobile UI integration

##### GET /compute-capital/status

SUPERINSTANCE INNOVATION: Compute Capital Economy implementation
REVOLUTIONARY: Users' productivity creates tradeable computational resources

### FishingLog AI Service

Commercial fishing intelligence and weather prediction AI

**Base URL:** `http://localhost:8096`

#### Endpoints

##### GET /health

Health Check

##### POST /fishinglog/insights

BREAKTHROUGH: Commercial and recreational fishing operations insights with cross-domain correlation
SUPERINSTANCE INNOVATION: Multi-domain intelligence leveraging all service success

##### GET /compute-capital/fishinglog-status

SUPERINSTANCE INNOVATION: Compute Capital Economy implementation for fishinglog
REVOLUTIONARY: User's fishinglog expertise creates tradeable computational resources

### DMLog AI Service

D&D campaign management and creative storytelling AI

**Base URL:** `http://localhost:8097`

#### Endpoints

##### GET /health

Health Check

##### POST /dmlog/insights

BREAKTHROUGH: Dungeon Master tools and campaign management insights with cross-domain correlation
SUPERINSTANCE INNOVATION: Multi-domain intelligence leveraging all service success

##### GET /compute-capital/dmlog-status

SUPERINSTANCE INNOVATION: Compute Capital Economy implementation for dmlog
REVOLUTIONARY: User's dmlog expertise creates tradeable computational resources

### BusinessLog AI Service

Enterprise analytics and cross-domain business intelligence

**Base URL:** `http://localhost:8098`

#### Endpoints

##### GET /health

Health Check

##### POST /businesslog/insights

BREAKTHROUGH: Enterprise logging and analytics insights with cross-domain correlation
SUPERINSTANCE INNOVATION: Multi-domain intelligence leveraging all service success

##### GET /compute-capital/businesslog-status

SUPERINSTANCE INNOVATION: Compute Capital Economy implementation for businesslog
REVOLUTIONARY: User's businesslog expertise creates tradeable computational resources

### Fitness Data API

Workout, nutrition, and biometric data management with AI integration

**Base URL:** `http://localhost:8099`

#### Endpoints

##### GET /fitness/profile

Get user's fitness profile

##### POST /fitness/profile

Create or update user's fitness profile

##### POST /fitness/workouts

Create a new workout session

##### GET /fitness/workouts

Get user's workout sessions with pagination

##### GET /fitness/workouts/{workout_id}

Get specific workout session

##### POST /fitness/nutrition

Create a nutrition entry

##### GET /fitness/nutrition

Get user's nutrition entries with filtering

##### POST /fitness/measurements

Create a body measurement entry

##### GET /fitness/measurements

Get user's body measurements

##### GET /fitness/analytics/summary

Get fitness analytics summary with AI insights integration

##### GET /health

Health check endpoint

