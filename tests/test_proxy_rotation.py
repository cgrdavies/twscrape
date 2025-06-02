import httpx
import pytest
from pytest_httpx import HTTPXMock

from twscrape.accounts_pool import AccountsPool
from twscrape.queue_client import QueueClient
from twscrape.proxies import get_active, ensure

URL = "https://example.com/api"


@pytest.mark.asyncio
async def test_rotate_on_proxy_error(pool_mock: AccountsPool, httpx_mock: HTTPXMock, monkeypatch):
    # Add proxies to the table
    await ensure("http://bad:8888")
    await ensure("http://working:8888")
    await ensure("http://backup:8888")

    # Account without preset proxy
    await pool_mock.add_account("user", "pass", "e", "e_pass")
    await pool_mock.set_active("user", True)

    # Force the first proxy selection to return the bad proxy
    sequence = iter(["http://bad:8888", "http://working:8888"])

    async def fake_get_active():
        return next(sequence, "http://working:8888")

    monkeypatch.setattr("twscrape.proxies.get_active", fake_get_active)

    async with QueueClient(pool_mock, "SearchTimeline") as c:
        httpx_mock.add_exception(httpx.ProxyError("bad proxy"))
        httpx_mock.add_response(url=URL, json={"ok": 1}, status_code=200)
        rep = await c.get(URL)
        assert rep.json() == {"ok": 1}

    # the original proxy should now be inactive
    active_proxy = await get_active()
    assert active_proxy != "http://bad:8888"
    assert active_proxy in ["http://working:8888", "http://backup:8888"]
