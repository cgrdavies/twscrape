import httpx
import pytest
from pytest_httpx import HTTPXMock

from twscrape.accounts_pool import AccountsPool
from twscrape.queue_client import QueueClient
from twscrape.proxies import get_active, ensure, get_proxy_id

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

    bad_id = await get_proxy_id("http://bad:8888")
    work_id = await get_proxy_id("http://working:8888")

    # Force the first proxy selection to return the bad proxy
    sequence = iter([(bad_id, "http://bad:8888"), (work_id, "http://working:8888")])

    async def fake_get_active():
        return next(sequence, (work_id, "http://working:8888"))

    monkeypatch.setattr("twscrape.proxies.get_active", fake_get_active)

    async with QueueClient(pool_mock, "SearchTimeline") as c:
        httpx_mock.add_exception(httpx.ProxyError("bad proxy"))
        httpx_mock.add_response(url=URL, json={"ok": 1}, status_code=200)
        rep = await c.get(URL)
        assert rep.json() == {"ok": 1}

    # the original proxy should now be inactive
    active_proxy = await get_active()
    assert active_proxy[1] != "http://bad:8888"
    assert active_proxy[1] in ["http://working:8888", "http://backup:8888"]

    acc = await pool_mock.get("user")
    assert acc.proxy_id == work_id
