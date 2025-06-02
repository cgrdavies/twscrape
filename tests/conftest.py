import os
import pytest

from twscrape.accounts_pool import AccountsPool
from twscrape.api import API
from twscrape.logger import set_log_level
from twscrape.queue_client import QueueClient, XClIdGenStore
from twscrape.db_pg import create_engine, set_engine, dispose_engine, execute

set_log_level("ERROR")


class ClIdGenMock:
    def calc(*args, **kwargs):
        return "mocked-clid"


@pytest.fixture(autouse=True)
def mock_xclidgenstore(monkeypatch):
    async def mock_get(*args, **kwargs):
        return ClIdGenMock()

    monkeypatch.setattr(XClIdGenStore, "get", classmethod(mock_get))


@pytest.fixture
async def pool_mock():
    # Set up test database URL
    test_db_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/twscrape_test"
    original_env = os.environ.get("TWSCRAPE_DATABASE_URL")
    os.environ["TWSCRAPE_DATABASE_URL"] = test_db_url

    # Ensure we start fresh
    await dispose_engine()

    # Create a fresh engine for this test
    engine = create_engine(test_db_url)
    set_engine(engine)

    try:
        pool = AccountsPool()

        # Clean up any existing test data before each test
        await execute("DELETE FROM accounts")

        yield pool

        # Clean up after each test
        await execute("DELETE FROM accounts")

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
