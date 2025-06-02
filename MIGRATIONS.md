# Database Migrations Guide

This guide explains how to run database migrations for the `twscrape` library in different environments.

## Overview

The `twscrape` library uses PostgreSQL with Alembic for database schema management. Before using the library, you need to ensure your database schema is up to date.

## Migration Methods

### 1. CLI Commands (Recommended)

The simplest way to run migrations is using the built-in CLI commands:

```bash
# Check migration status
twscrape migration_status

# Run migrations
twscrape migrate

# Create new migration (for developers)
twscrape create_migration "description of changes"
```

### 2. Programmatic API

For applications that need to run migrations programmatically:

```python
import twscrape

# Check if migrations are needed
status = twscrape.check_migration_status()
if status.get('needs_migration'):
    print("Running migrations...")
    success = twscrape.init_database()
    if success:
        print("Migrations completed successfully")
    else:
        print("Migration failed")
        exit(1)
```

### 3. Docker Environments

For containerized applications, use the standalone migration script:

```bash
# Basic usage
python scripts/migrate.py

# Wait for database to become available (useful in docker-compose)
python scripts/migrate.py --wait-for-db --timeout 60

# Check only (useful for health checks)
python scripts/migrate.py --check-only
```

## Docker Integration Examples

### Docker Compose with Init Container

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: twscrape
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  migrate:
    build: .
    depends_on:
      - postgres
    environment:
      TWSCRAPE_DATABASE_URL: postgresql://postgres:postgres@postgres:5432/twscrape
    command: python scripts/migrate.py --wait-for-db
    restart: "no"

  app:
    build: .
    depends_on:
      migrate:
        condition: service_completed_successfully
    environment:
      TWSCRAPE_DATABASE_URL: postgresql://postgres:postgres@postgres:5432/twscrape
    command: python your_app.py

volumes:
  postgres_data:
```

### Dockerfile with Migration

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Install twscrape
RUN pip install -e .

# Create migration script entrypoint
COPY scripts/migrate.py /usr/local/bin/migrate
RUN chmod +x /usr/local/bin/migrate

# Default command runs migrations then starts app
CMD ["sh", "-c", "python scripts/migrate.py --wait-for-db && python your_app.py"]
```

### Kubernetes Init Container

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: twscrape-app
spec:
  template:
    spec:
      initContainers:
      - name: migrate
        image: your-app:latest
        command: ["python", "scripts/migrate.py", "--wait-for-db"]
        env:
        - name: TWSCRAPE_DATABASE_URL
          value: "postgresql://user:pass@postgres:5432/twscrape"
      containers:
      - name: app
        image: your-app:latest
        command: ["python", "your_app.py"]
        env:
        - name: TWSCRAPE_DATABASE_URL
          value: "postgresql://user:pass@postgres:5432/twscrape"
```

## Environment Variables

Configure your database connection using environment variables:

```bash
# Required: PostgreSQL connection string
export TWSCRAPE_DATABASE_URL="postgresql://user:password@host:port/database"

# Optional: For asyncpg (recommended for async applications)
export TWSCRAPE_DATABASE_URL="postgresql+asyncpg://user:password@host:port/database"
```

## Migration Status Codes

The migration commands return specific exit codes for automation:

- `0`: Success (migrations completed or not needed)
- `1`: Error (migration failed or database unreachable)

For `--check-only` mode:
- `0`: Database is up to date
- `1`: Migrations are needed

## Troubleshooting

### Common Issues

1. **"No module named 'psycopg2'"**
   - Install: `pip install psycopg2-binary`
   - This is required for synchronous database operations during migrations

2. **"Database connection failed"**
   - Check your `TWSCRAPE_DATABASE_URL` environment variable
   - Ensure PostgreSQL is running and accessible
   - Verify credentials and database name

3. **"asyncio.run() cannot be called from a running event loop"**
   - This should be automatically handled by the migration system
   - If you encounter this, try using the standalone script instead of the CLI

### Database Connection Testing

Test your database connection:

```python
from twscrape.migrations.utils import check_migration_status

status = check_migration_status()
if "error" in status:
    print(f"Database error: {status['error']}")
else:
    print("Database connection successful")
```

## Development

For library developers who need to create new migrations:

```bash
# Auto-generate migration from model changes
twscrape create_migration "add new table"

# Create empty migration for manual changes
twscrape create_migration "custom changes" --no-autogenerate
```

## Best Practices

1. **Always run migrations before starting your application**
2. **Use init containers in production deployments**
3. **Test migrations on a copy of production data**
4. **Monitor migration logs for errors**
5. **Keep database backups before running migrations**

## Support

If you encounter issues with migrations:

1. Check the [troubleshooting section](#troubleshooting)
2. Verify your environment variables
3. Test database connectivity
4. Check the GitHub issues for similar problems
