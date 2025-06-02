# Migration Quick Start

The `twscrape` library requires PostgreSQL database migrations to be run before first use.

## Quick Commands

```bash
# Check if migrations are needed
twscrape migration_status

# Run migrations
twscrape migrate
```

## Docker Users

Use the provided migration script in your containers:

```bash
# In your Dockerfile or docker-compose
python scripts/migrate.py --wait-for-db
```

## Programmatic Usage

```python
import twscrape

# Check and run migrations if needed
status = twscrape.check_migration_status()
if status.get('needs_migration'):
    twscrape.init_database()
```

## Complete Examples

- **Docker Setup**: See `examples/docker/` for a complete Docker Compose example
- **Detailed Guide**: See `MIGRATIONS.md` for comprehensive documentation

## Environment Variables

```bash
export TWSCRAPE_DATABASE_URL="postgresql://user:pass@host:port/database"
```

For async applications, use:
```bash
export TWSCRAPE_DATABASE_URL="postgresql+asyncpg://user:pass@host:port/database"
```

## Dependencies

Migrations require `psycopg2-binary` for synchronous database access:
```bash
pip install psycopg2-binary
```

This is automatically included when you install `twscrape`.
