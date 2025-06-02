# Docker Example for twscrape

This example demonstrates how to use `twscrape` in a Docker environment with proper database migration handling.

## Architecture

- **postgres**: PostgreSQL database container
- **migrate**: Init container that runs database migrations
- **app**: Main application container that uses twscrape

## Quick Start

1. **Build and run the stack:**
   ```bash
   docker-compose up --build
   ```

2. **View logs:**
   ```bash
   # Migration logs
   docker-compose logs migrate

   # Application logs
   docker-compose logs app
   ```

3. **Add accounts (optional):**
   ```bash
   # Create accounts file
   echo "username1:password1:email1@example.com:email_password1" > accounts.txt

   # Add accounts to the running container
   docker-compose exec app twscrape add_accounts /app/accounts.txt username:password:email:email_password

   # Login accounts
   docker-compose exec app twscrape login_accounts
   ```

## How It Works

### 1. Database Setup
The `postgres` service provides a PostgreSQL database with health checks.

### 2. Migration Init Container
The `migrate` service:
- Waits for the database to become available
- Runs database migrations using `scripts/migrate.py`
- Exits after successful migration
- Blocks the main app from starting until migrations complete

### 3. Main Application
The `app` service:
- Starts only after migrations complete successfully
- Demonstrates basic twscrape usage
- Shows how to check migration status programmatically
- Provides a simple heartbeat to keep the container running

## Key Features

- **Automatic migration handling**: Database schema is set up automatically
- **Health checks**: Ensures database is ready before running migrations
- **Dependency management**: App waits for migrations to complete
- **Error handling**: Proper exit codes for container orchestration
- **Development friendly**: Easy to modify and test

## Production Considerations

For production use, consider:

1. **Persistent volumes**: Database data is already persisted
2. **Secrets management**: Use Docker secrets or environment files for credentials
3. **Resource limits**: Add memory and CPU limits to services
4. **Monitoring**: Add health checks to the app service
5. **Backup strategy**: Regular database backups
6. **Security**: Use non-root users, scan images for vulnerabilities

## Customization

### Environment Variables

Modify the database connection in `docker-compose.yml`:

```yaml
environment:
  TWSCRAPE_DATABASE_URL: postgresql+asyncpg://user:pass@host:port/database
```

### Application Code

Modify `app.py` to implement your specific use case:

```python
# Your custom application logic
async def your_function():
    pool = AccountsPool()
    api = API(pool)

    # Your twscrape usage here
    async for tweet in api.search("your query"):
        print(tweet.rawContent)
```

## Troubleshooting

### Migration Issues

Check migration logs:
```bash
docker-compose logs migrate
```

Common issues:
- Database connection timeout: Increase `--timeout` value
- Permission errors: Check database credentials
- Network issues: Verify service connectivity

### Application Issues

Check app logs:
```bash
docker-compose logs app
```

Connect to the app container for debugging:
```bash
docker-compose exec app bash
twscrape migration_status
twscrape accounts
```

## Cleanup

Remove all containers and volumes:
```bash
docker-compose down -v
```
