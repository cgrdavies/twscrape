# Contributor Guide

## Project Overview

**twscrape** is a Python library that implements Twitter's GraphQL and Search APIs with SNScrape data models. This is an async-first library that supports:

- Twitter/X API scraping with account management and rate limiting
- Both Search and GraphQL API endpoints
- Account session management with cookie support
- Email verification via IMAP for account login
- Database persistence using PostgreSQL
- CLI tools for command-line usage

### Key Directories and Files

- `twscrape/` - Main package source code
  - `api.py` - Core API implementation
  - `models.py` - Twitter data models (Tweet, User, etc.)
  - `accounts_pool.py` - Account management and rotation
  - `login.py` - Authentication and login flows
  - `cli.py` - Command-line interface
  - `migrations/` - Database schema migrations
- `tests/` - Test suite with mocked data
- `examples/` - Usage examples
- `scripts/` - Utility scripts
- `pyproject.toml` - Project configuration and dependencies
- `Makefile` - Development commands

## Development Environment Setup

### Prerequisites
- Python 3.10+ (supports 3.10, 3.11, 3.12, 3.13)
- PostgreSQL database

### Installation
```bash
# Install in development mode with dev dependencies
pip install -e .[dev]

# Or use the Makefile command
make install
```

### Environment Variables
- Set up database connection if using PostgreSQL
- Check `setup_db_env.sh` for database configuration examples

## Code Style and Guidelines

### Python Code Standards
- Use **async/await** patterns throughout - this is an async-first library
- Follow existing code patterns in `api.py` and `models.py`
- Type hints are required for all public methods
- Use `loguru` for logging (see `logger.py`)
- Error handling should be comprehensive given the API scraping context

### Import Organization
- Use relative imports within the package
- External dependencies: `httpx` for HTTP, `asyncpg`/`psycopg2` for database
- Models should inherit from SNScrape patterns

### Database Changes
- Use Alembic migrations for schema changes (see `migrations/` directory)
- Test migrations both up and down
- Update `db_models.py` for new database models

## Testing Instructions

### Running Tests
```bash
# Run full test suite with coverage
make test

# Run tests with coverage report
make test-cov

# Run linting and tests together
make check

# Test across Python versions (requires Docker)
make test-matrix-py
```

### Test Structure
- Tests use `pytest` with `pytest-asyncio` for async testing
- Mock data stored in `tests/mocked-data/` directory
- Use `pytest-httpx` for mocking HTTP requests
- All async tests should use proper async test patterns

### Adding Tests
- Add tests for any new API endpoints
- Include both success and error scenarios
- Mock external API calls - don't hit real Twitter API in tests
- Update mock data when API responses change (see `make update-mocks`)

## Linting and Code Quality

### Available Commands
```bash
# Format code and run all linters
make lint

# Individual steps:
python -m ruff check --select I --fix .  # Fix import order
python -m ruff format .                  # Format code
python -m ruff check .                   # Check style
python -m pyright .                      # Type checking
```

### Requirements
- **Ruff** for code formatting and linting
- **Pyright** for type checking
- All code must pass linting before merge
- Type errors must be resolved

## API Development Guidelines

### Adding New Endpoints
1. Add the endpoint method to `api.py`
2. Create corresponding models in `models.py` if needed
3. Add CLI command in `cli.py` if appropriate
4. Include comprehensive error handling
5. Add both sync (gather) and async (generator) versions
6. Update mock data for tests

### Account Management
- Be mindful of rate limiting and account rotation
- Use the `accounts_pool.py` for account management
- Handle login failures and account locks gracefully
- Support both cookie-based and credential-based accounts

### Error Handling
- Use appropriate HTTP status code handling
- Implement retry logic for transient failures
- Log errors appropriately with context
- Handle Twitter API rate limits gracefully

## Database Migrations

### Creating Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Migration Guidelines
- Always test migrations on sample data
- Include both upgrade and downgrade logic
- Document breaking changes in migration comments
- Update seed data if needed

## CLI Development

### Adding CLI Commands
- Add new commands to `cli.py`
- Follow existing pattern for argument parsing
- Include proper help text and examples
- Handle both interactive and batch modes
- Support common output formats (JSON, text)

### CLI Testing
- Test CLI commands work with various input formats
- Ensure error messages are user-friendly
- Verify help text is accurate and helpful

## Pull Request Guidelines

### PR Title Format
`[component] Brief description`

Examples:
- `[api] Add support for Twitter Spaces endpoints`
- `[cli] Improve account management commands`
- `[models] Update Tweet model for new API fields`
- `[tests] Add integration tests for search functionality`

### PR Checklist
- [ ] Code passes all linting (`make lint`)
- [ ] Tests pass (`make test`)
- [ ] New functionality includes tests
- [ ] Documentation updated if needed
- [ ] Database migrations included if schema changed
- [ ] CLI help text updated for new commands
- [ ] Breaking changes documented in PR description

### Code Review Focus Areas
- Async/await usage correctness
- Error handling and edge cases
- Rate limiting and account management
- Database query efficiency
- API response parsing accuracy
- Memory usage for large data sets

## Release Process

### Version Management
- Version is managed in `pyproject.toml`
- Releases are automated via GitHub Actions on version tags
- Follow semantic versioning (MAJOR.MINOR.PATCH)

### Release Checklist
- Update version in `pyproject.toml`
- Update changelog/release notes
- Ensure all tests pass across Python versions
- Tag release: `git tag vX.Y.Z`
- Push tag to trigger automated release

## Security Considerations

- **Never commit account credentials or cookies**
- Use environment variables for sensitive configuration
- Be mindful of rate limiting to avoid account bans
- Handle user data responsibly and in compliance with Twitter ToS
- Validate all user inputs in CLI commands

## Performance Guidelines

- Use async generators for large data sets
- Implement proper pagination for API endpoints
- Monitor memory usage when processing large volumes
- Use connection pooling for database operations
- Consider implementing caching for frequently accessed data

## Debugging and Troubleshooting

### Debug Mode
```bash
# Enable debug logging
twscrape --debug <command>

# Or programmatically
from twscrape.logger import set_log_level
set_log_level("DEBUG")
```

### Common Issues
- Account login failures: Check email/password and IMAP settings
- Rate limiting: Ensure proper account rotation
- Database connection issues: Verify PostgreSQL setup
- Import errors: Check Python version compatibility

### Development Tips
- Use the `--raw` flag in CLI to see actual API responses
- Monitor account status regularly during development
- Use small limits during testing to avoid rate limits
- Keep test data separate from production accounts
