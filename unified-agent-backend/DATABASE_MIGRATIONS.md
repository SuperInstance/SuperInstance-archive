# Database Migrations Guide

This document provides comprehensive information about database migrations for the unified-agent-backend project.

## Overview

The project uses Alembic for database migrations, providing version control for schema changes and data seeding. All database models are defined in SQLAlchemy ORM and migrations are generated automatically.

## Database Models

### Core Models

1. **Agents** (`agents` table)
   - AI agents with capabilities, configuration, and performance metrics
   - Status tracking (active, idle, busy, error, maintenance, decommissioned)
   - Health monitoring and performance tracking
   - Tools assignments and constraints

2. **Workflows** (`workflows` table)
   - DAG-based workflow definitions and execution
   - Node and edge management
   - Template system for reusable workflows
   - Execution tracking and statistics

3. **Workflow Nodes** (`workflow_nodes` table)
   - Individual workflow steps
   - Configuration and execution parameters
   - Position information for visualization
   - Retry mechanisms

4. **Workflow Executions** (`workflow_executions` table)
   - Individual workflow runs
   - State tracking and checkpointing
   - Error handling and recovery
   - Performance metrics

5. **Tools** (`tools` table)
   - Available tools for agents
   - Configuration and parameter schemas
   - Usage tracking and statistics
   - Authentication and security settings

6. **Agent-Tool Relationships** (`agent_tools` table)
   - Many-to-many relationship between agents and tools
   - Assignment-specific configuration
   - Usage limits and rate limiting
   - Permission management

7. **Execution Snapshots** (`execution_snapshots` table)
   - Intermediate state capture during workflow execution
   - Checkpointing for recovery
   - Debugging and audit information
   - Performance and resource usage tracking

## Migration Files

### Migration Structure

```
src/alembic/
├── versions/
│   ├── 001_initial_migration.py      # Initial schema creation
│   ├── 002_insert_default_tools.py   # Default tools seeding
│   └── ...                           # Future migrations
├── env.py                           # Alembic environment configuration
├── script.py.mako                   # Migration template
└── alembic.ini                      # Alembic configuration
```

### Migration 001: Initial Schema

Creates all database tables with proper:
- Primary keys and foreign keys
- Indexes for performance optimization
- Constraints for data integrity
- Check constraints for enum values
- Unique constraints for business rules

### Migration 002: Default Tools

Inserts 10 default tools into the database:
1. Text Generation - AI text generation using language models
2. Code Generation - Code generation in multiple languages
3. Data Analysis - Structured data analysis and processing
4. Web Search - Web search functionality
5. File Operations - File read/write/manipulation
6. Email Sender - SMTP email sending
7. API Caller - HTTP requests to external APIs
8. Database Query - SQL query execution
9. Image Processing - Image manipulation and processing
10. Document Parser - Document text extraction

## Using Migrations

### Available Commands

```bash
# Run all pending migrations
make migrate

# Create a new migration with autogenerate
make migrate-create message="Add new feature"

# Create an empty migration (for manual SQL)
make migrate-create-empty message="Manual SQL changes"

# Rollback one migration
make migrate-down

# Show migration history
make migrate-history

# Show current migration version
make migrate-current

# Set migration version without running (useful for fresh DB)
make migrate-stamp

# Reset database completely (WARNING: deletes all data)
make db-reset
```

### Direct Alembic Commands

```bash
# Run migrations directly
PYTHONPATH=src alembic -c src/alembic.ini upgrade head

# Create migration
PYTHONPATH=src alembic -c src/alembic.ini revision --autogenerate -m "Description"

# Rollback
PYTHONPATH=src alembic -c src/alembic.ini downgrade -1

# Show history
PYTHONPATH=src alembic -c src/alembic.ini history
```

## Database Seeding

### Sample Data Script

The `src/scripts/seed_data.py` script creates sample data for development:

- 4 Sample agents with different capabilities
- 3 Sample workflows (2 templates, 1 custom)
- Tool assignments based on agent capabilities

### Running Seeding

```bash
# Seed the database with sample data
make seed

# Or run directly
PYTHONPATH=src python -m scripts.seed_data
```

## Schema Changes Workflow

### 1. Model Changes

1. Modify models in `src/app/models/`
2. Update relationships and constraints as needed
3. Add validation methods for new fields
4. Update model imports in `__init__.py`

### 2. Generate Migration

```bash
# Generate migration with changes
make migrate-create message="Add new feature to model"
```

### 3. Review Migration

- Check generated SQL in the migration file
- Add custom SQL if needed for complex changes
- Ensure proper indexes and constraints
- Test both upgrade and downgrade functions

### 4. Test Migration

```bash
# Test on development database
make migrate

# Test rollback
make migrate-down
make migrate
```

### 5. Apply to Production

- Always test migrations on staging first
- Backup production database before migration
- Apply migration during maintenance window if needed
- Monitor application after migration

## Database Configuration

### Environment Variables

```bash
# Database connection
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/unified_agent_db

# Alternative format
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=unified_agent_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
```

### Connection Settings

The application uses async SQLAlchemy with:
- Connection pooling for performance
- Automatic retry on connection failures
- Query timeouts for long-running operations
- Connection health checks

## Best Practices

### Migration Development

1. **Descriptive Messages**: Use clear, descriptive migration messages
2. **Atomic Changes**: Each migration should be a single logical change
3. **Backward Compatibility**: Consider impact on existing data
4. **Testing**: Always test both upgrade and downgrade paths
5. **Documentation**: Document complex changes in comments

### Performance Considerations

1. **Indexes**: Add indexes for frequently queried columns
2. **Constraints**: Use database constraints for data integrity
3. **Batch Operations**: Use batch processing for large data changes
4. **Locking**: Be aware of table locks during migrations
5. **Monitoring**: Monitor migration performance on large datasets

### Data Integrity

1. **Foreign Keys**: Always use foreign key constraints
2. **Check Constraints**: Validate data ranges and formats
3. **Unique Constraints**: Prevent duplicate data
4. **Not Null**: Require essential fields
5. **Default Values**: Provide sensible defaults

## Troubleshooting

### Common Issues

1. **Migration Dependencies**: Ensure migrations are applied in order
2. **Database Connection**: Check DATABASE_URL configuration
3. **Permissions**: Ensure database user has required permissions
4. **Locks**: Check for long-running transactions
5. **Disk Space**: Ensure sufficient space for migrations

### Recovery

```bash
# Check current migration version
make migrate-current

# Rollback to specific version
PYTHONPATH=src alembic -c src/alembic.ini downgrade <revision_id>

# Re-apply migrations
make migrate

# Reset to known state (WARNING: data loss)
make db-reset
```

## Production Considerations

### Pre-deployment Checklist

- [ ] Test migrations on staging environment
- [ ] Backup production database
- [ ] Review migration scripts for potential issues
- [ ] Schedule maintenance window if needed
- [ ] Prepare rollback plan
- [ ] Monitor application health after deployment

### Monitoring

- Monitor migration execution time
- Check for application errors after deployment
- Monitor database performance metrics
- Verify data integrity after migration
- Monitor error rates and response times

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Database Best Practices](https://github.com/x-team/database-best-practices)

## Support

For questions or issues with database migrations:
1. Check this documentation first
2. Review existing migration files for examples
3. Test changes in development environment
4. Contact the development team for assistance