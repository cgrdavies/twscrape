import os
import pytest

from twscrape.accounts_pool import AccountsPool
from twscrape.api import API
from twscrape.logger import set_log_level
from twscrape.queue_client import QueueClient, XClIdGenStore
from twscrape.db_pg import create_engine, set_engine, dispose_engine, execute
from twscrape.migrations.utils import run_migrations
from twscrape.config import get_database_url

set_log_level("ERROR")


class ClIdGenMock:
    def calc(*args, **kwargs):
        return "mocked-clid"


@pytest.fixture(autouse=True)
def mock_xclidgenstore(monkeypatch):
    async def mock_get(*args, **kwargs):
        return ClIdGenMock()

    monkeypatch.setattr(XClIdGenStore, "get", classmethod(mock_get))


async def ensure_test_database(test_db_url):
    """Ensure the test database exists by creating it if necessary."""
    import asyncpg
    from urllib.parse import urlparse

    # Parse the test database URL to get connection info
    parsed = urlparse(test_db_url)

    # Extract database name from path
    test_db_name = parsed.path.lstrip('/')

    # Create connection URL to postgres database (for creating the test DB)
    postgres_url = test_db_url.replace(f"/{test_db_name}", "/postgres")

    # Remove +asyncpg for asyncpg raw connection
    connection_url = postgres_url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        # Connect to postgres database to create the test database
        conn = await asyncpg.connect(connection_url)

        # Check if test database exists
        result = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", test_db_name
        )

        if not result:
            # Create the test database
            await conn.execute(f'CREATE DATABASE "{test_db_name}"')
            print(f"✅ Created test database: {test_db_name}")

        await conn.close()

    except Exception as e:
        # If we can't create the database, it might already exist or we might not have permissions
        # Let the test continue and let it fail with a more specific error if needed
        print(f"⚠️  Could not ensure test database exists: {e}")


@pytest.fixture
async def pool_mock():
    # Get the base database URL from environment/config
    base_db_url = get_database_url()

    # Create test database URL by appending _test to the database name
    # Handle both cases: with and without trailing database name
    if base_db_url.endswith("/twscrape"):
        test_db_url = base_db_url + "_test"
    elif "/twscrape?" in base_db_url:
        # Handle case with query parameters
        test_db_url = base_db_url.replace("/twscrape?", "/twscrape_test?")
    else:
        # Extract the base URL and append the test database name
        # Format: postgresql+asyncpg://user:pass@host:port/database
        url_parts = base_db_url.rsplit("/", 1)
        if len(url_parts) == 2:
            base_url, db_name = url_parts
            test_db_url = f"{base_url}/{db_name}_test"
        else:
            # Fallback to default test configuration
            test_db_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/twscrape_test"

    # Ensure the test database exists
    await ensure_test_database(test_db_url)

    original_env = os.environ.get("TWSCRAPE_DATABASE_URL")
    os.environ["TWSCRAPE_DATABASE_URL"] = test_db_url

    # Ensure we start fresh
    await dispose_engine()

    # Create a fresh engine for this test
    engine = create_engine(test_db_url)
    set_engine(engine)

    try:
        # Run migrations to ensure all tables are created
        success = run_migrations()
        if not success:
            raise RuntimeError("Failed to run migrations for test database")

        pool = AccountsPool()

        # Clean up any existing test data before each test
        await execute("DELETE FROM accounts")
        await execute("DELETE FROM proxies")

        yield pool

        # Clean up after each test
        await execute("DELETE FROM accounts")
        await execute("DELETE FROM proxies")

    finally:
        # Clean up engine and restore environment
        await dispose_engine()
        if original_env is not None:
            os.environ["TWSCRAPE_DATABASE_URL"] = original_env
        else:
            os.environ.pop("TWSCRAPE_DATABASE_URL", None)


@pytest.fixture
async def client_fixture(pool_mock: AccountsPool):
    pool_mock._order_by = "username"

    for x in range(1, 3):
        await pool_mock.add_account(f"user{x}", f"pass{x}", f"email{x}", f"email_pass{x}")
        await pool_mock.set_active(f"user{x}", True)

    client = QueueClient(pool_mock, "SearchTimeline")
    yield pool_mock, client


@pytest.fixture
async def api_mock(pool_mock: AccountsPool):
    await pool_mock.add_account("user1", "pass1", "email1", "email_pass1")
    await pool_mock.set_active("user1", True)

    api = API(pool_mock)
    yield api
