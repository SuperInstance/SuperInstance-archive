# Hatchery Management

Business incubation pipeline and startup hatchery management system

## Overview

This service was generated on 2025-08-25 using the ActiveLog service generator.

## Configuration

- **Port**: 8441
- **Health Check**: `GET /health`
- **API Documentation**: `GET /docs`

## Development

### Running the Service

```bash
# Using the CLI
python dev-tools/cli/activelog_cli.py services start hatchery_management

# Direct execution
cd services/hatchery_management
python -m uvicorn main:app --host 0.0.0.0 --port 8441 --reload
```

### Testing

```bash
# Run service tests
python -m pytest tests/services/hatchery_management/

# Run with coverage
python -m pytest tests/services/hatchery_management/ --cov=services/hatchery_management
```

### API Endpoints

- `GET /health` - Health check
- `GET /info` - Service information
- `GET /docs` - API documentation (Swagger UI)
- `GET /redoc` - API documentation (ReDoc)

## Dependencies

- FastAPI
- Pydantic
- SQLAlchemy (if using database)
- Redis (if using caching)

## Environment Variables

- `DATABASE_URL` - Database connection string
- `REDIS_URL` - Redis connection string
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `ENVIRONMENT` - Environment (development, staging, production)

## Contributing

1. Make changes to the service code
2. Add/update tests
3. Run tests and ensure they pass
4. Update documentation if needed
5. Submit a pull request

## Generated Files

This service was generated from the `default` template and includes:

- FastAPI application setup
- Basic API endpoints
- Database models (if applicable)
- Test structure
- Docker configuration
- Documentation

## Next Steps

1. Customize the generated code for your specific requirements
2. Add your business logic
3. Implement additional API endpoints
4. Add comprehensive tests
5. Update documentation
