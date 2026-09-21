#!/bin/sh
# PostgreSQL health check script

set -e

# Check if PostgreSQL is accepting connections
pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" -h localhost -p 5432

if [ $? -eq 0 ]; then
    echo "PostgreSQL health check passed"
    exit 0
else
    echo "PostgreSQL health check failed"
    exit 1
fi