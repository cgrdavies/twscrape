import argparse

import pytest

from twscrape.cli import main
from twscrape.db_pg import fetchall


@pytest.mark.asyncio
async def test_cli_add_and_list_accounts(pool_mock, tmp_path, monkeypatch):
    # prepare accounts file
    file = tmp_path / "accounts.txt"
    file.write_text("user1:pass1:email1:ep1\nuser2:pass2:email2:ep2\n")
    args = argparse.Namespace(
        command="add_accounts",
        file_path=str(file),
        line_format="username:password:email:email_password",
        debug=False,
        raw=False,
    )
    await main(args)

    captured = []
    monkeypatch.setattr(
        "twscrape.cli.print_table", lambda rows, hr_after=False: captured.append(rows)
    )
    args = argparse.Namespace(command="accounts", debug=False, raw=False)
    await main(args)

    assert len(captured) == 1
    usernames = {row["username"] for row in captured[0]}
    assert usernames == {"user1", "user2"}


@pytest.mark.asyncio
async def test_cli_delete_accounts(pool_mock):
    await pool_mock.add_account("u1", "p1", "e1", "ep1")
    await pool_mock.add_account("u2", "p2", "e2", "ep2")

    args = argparse.Namespace(command="del_accounts", usernames=["u1"], debug=False, raw=False)
    await main(args)

    rows = await fetchall("SELECT username FROM accounts ORDER BY username")
    assert [r[0] for r in rows] == ["u2"]


@pytest.mark.asyncio
async def test_cli_stats(pool_mock, monkeypatch):
    await pool_mock.add_account("u1", "p1", "e1", "ep1")
    await pool_mock.set_active("u1", True)
    from twscrape.utils import utc

    await pool_mock.lock_until("u1", "SearchTimeline", utc.ts() + 60)

    captured = []
    monkeypatch.setattr(
        "twscrape.cli.print_table", lambda rows, hr_after=False: captured.append(rows)
    )
    args = argparse.Namespace(command="stats", debug=False, raw=False)
    await main(args)

    assert captured and captured[0][0]["queue"] == "locked_SearchTimeline"
