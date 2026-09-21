# Unified Agent Backend

A comprehensive backend system for AI agents built with FastAPI, featuring async support, vector storage, real-time communication, and robust monitoring capabilities.

## 🚀 Features

- **FastAPI Framework**: Modern, fast (high-performance) web framework for building APIs
- **Async Support**: Full async/await support for improved performance
- **Database Integration**: PostgreSQL with SQLAlchemy ORM and async support
- **Vector Storage**: Qdrant integration for similarity search and document embeddings
- **Caching Layer**: Redis for high-performance caching and session management
- **Real-time Communication**: WebSocket support for live interactions
- **Background Tasks**: Celery integration for async task processing
- **Authentication & Security**: JWT-based authentication with comprehensive security features
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation
- **Monitoring & Metrics**: Prometheus metrics integration
- **Containerization**: Docker and Docker Compose support
- **Testing**: Comprehensive test suite with pytest
- **Code Quality**: Pre-commit hooks with black, ruff, mypy, and more

## 📁 Project Structure

```
unified-agent-backend/
├── src/
│   ├── app/
│   │   ├── api/                # API endpoints and routing
│   │   │   ├── v1/            # API version 1
│   │   │   └── deps/          # API dependencies
│   │   ├── core/              # Core application logic
│   │   │   ├── config/        # Configuration management
│   │   │   ├── security/      # Security and authentication
│   │   │   └── logging/       # Logging configuration
│   │   ├── db/                # Database configuration and connections
│   │   ├── models/            # SQLAlchemy models
│   │   │   ├── base/          # Base model classes
│   │   │   ├── agent/         # Agent-related models
│   │   │   ├── chat/          # Chat-related models
│   │   │   ├── document/      # Document models
│   │   │   └── health/        # Health check models
│   │   ├── schemas/           # Pydantic schemas for request/response
│   │   ├── services/          # Business logic services
│   │   │   ├── agent/         # Agent services
│   │   │   ├── chat/          # Chat services
│   │   │   ├── document/      # Document services
│   │   │   └── health/        # Health check services
│   │   ├── utils/             # Utility functions and helpers
│   │   │   ├── exceptions/    # Custom exceptions
│   │   │   └── helpers/       # Helper functions
│   │   ├── middleware/        # Custom middleware
│   │   └── __init__.py
│   ├── tests/                 # Test suite
│   │   ├── unit/             # Unit tests
│   │   ├── integration/      # Integration tests
│   │   └── e2e/              # End-to-end tests
│   ├── alembic/              # Database migrations
│   └── scripts/              # Utility scripts
├── docker-compose.yml         # Development environment
├── Dockerfile                 # Production container
├── pyproject.toml            # Project configuration
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore file
├── .pre-commit-config.yaml   # Pre-commit hooks configuration
└── README.md                 # This file
```

## 🛠️ Technology Stack

- **Backend**: FastAPI, Uvicorn, Pydantic
- **Database**: PostgreSQL, SQLAlchemy (async)
- **Cache**: Redis
- **Vector Storage**: Qdrant
- **Authentication**: JWT, python-jose, passlib
- **Background Tasks**: Celery, Redis
- **Real-time**: WebSockets (python-socketio)
- **Testing**: pytest, pytest-asyncio
- **Code Quality**: Black, Ruff, MyPy, Pre-commit
- **Containerization**: Docker, Docker Compose
- **Monitoring**: Prometheus
- **Documentation**: OpenAPI/Swagger

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL (if not using Docker)
- Redis (if not using Docker)
- Qdrant (if not using Docker)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd unified-agent-backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Set up pre-commit hooks**
   ```bash
   pre-commit install
   ```

### Running with Docker Compose (Recommended)

1. **Start all services**
   ```bash
   docker-compose up -d
   ```

2. **Run database migrations**
   ```bash
   docker-compose exec app alembic upgrade head
   ```

3. **Access the application**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

### Running Locally

1. **Start services (Redis, PostgreSQL, Qdrant)**
   ```bash
   docker-compose up -d redis postgres qdrant
   ```

2. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

3. **Start the application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## 📝 Development

### Code Quality

The project uses several tools to maintain code quality:

- **Black**: Code formatting
- **Ruff**: Linting and import sorting
- **MyPy**: Static type checking
- **Pre-commit**: Git hooks for automated checks

Run them manually:
```bash
black src/
ruff check src/ --fix
mypy src/
```

### Testing

Run the test suite:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=src/app --cov-report=html
```

Run specific test types:
```bash
pytest src/tests/unit/          # Unit tests only
pytest src/tests/integration/   # Integration tests only
pytest src/tests/e2e/          # End-to-end tests only
```

### Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback migrations:
```bash
alembic downgrade -1
```

### Environment Variables

Key environment variables (see `.env.example` for complete list):

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `QDRANT_HOST`: Qdrant server host
- `SECRET_KEY`: JWT secret key
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key

## 🐳 Docker

### Development Docker Compose

The `docker-compose.yml` includes:
- Application server
- PostgreSQL database
- Redis cache
- Qdrant vector database
- Celery worker
- Flower (Celery monitoring)

### Production Docker Build

```bash
docker build -t unified-agent-backend .
```

## 📊 Monitoring

### Prometheus Metrics

Access metrics at:
- Metrics endpoint: http://localhost:8000/metrics
- Prometheus: http://localhost:9090 (if enabled)

### Health Checks

- Health endpoint: http://localhost:8000/health
- Detailed health: http://localhost:8000/health/detailed

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and code quality checks
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Contact the development team

## 🔄 API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

The API includes comprehensive documentation with examples for all endpoints.