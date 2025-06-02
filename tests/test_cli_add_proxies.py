import argparse

import pytest

from twscrape.cli import main
from twscrape.db_pg import fetchall


@pytest.mark.asyncio
async def test_cli_add_proxies(pool_mock, tmp_path):
    file = tmp_path / "proxies.txt"
    file.write_text("http://p1:8080\nhttp://p2:8080\n")

    args = argparse.Namespace(command="add_proxies", file_path=str(file), debug=False, raw=False)
    await main(args)
    await main(args)

    rows = await fetchall("SELECT url FROM proxies ORDER BY id")
    urls = [r[0] for r in rows]
    assert urls == ["http://p1:8080", "http://p2:8080"]
