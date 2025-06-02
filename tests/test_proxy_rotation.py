import httpx
import pytest
from pytest_httpx import HTTPXMock

from twscrape.accounts_pool import AccountsPool
from twscrape.queue_client import QueueClient
from twscrape.proxies import get_active

URL = "https://example.com/api"


@pytest.mark.asyncio
async def test_rotate_on_proxy_error(pool_mock: AccountsPool, httpx_mock: HTTPXMock):
    # one working + one broken proxy in DB
    await pool_mock.add_account("user", "pass", "e", "e_pass", proxy="http://bad:8888")
    await pool_mock.set_active("user", True)

    async with QueueClient(pool_mock, "SearchTimeline") as c:
        httpx_mock.add_exception(httpx.ProxyError("bad proxy"))
        httpx_mock.add_response(url=URL, json={"ok": 1}, status_code=200)
        rep = await c.get(URL)
        assert rep.json() == {"ok": 1}

    # the original proxy should now be inactive
    assert (await get_active()) != "http://bad:8888"
