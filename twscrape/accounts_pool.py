import asyncio
import uuid
from datetime import datetime, timezone
from typing import TypedDict

from fake_useragent import UserAgent
from httpx import HTTPStatusError

from .account import Account
from .db_pg import execute, fetchall, fetchone
from .logger import logger
from .login import LoginConfig, login
from .utils import get_env_bool, parse_cookies, utc


class NoAccountError(Exception):
    pass


class AccountInfo(TypedDict):
    username: str
    logged_in: bool
    active: bool
    last_used: datetime | None
    total_req: int
    error_msg: str | None


def guess_delim(line: str):
    lp, rp = tuple([x.strip() for x in line.split("username")])
    return rp[0] if not lp else lp[-1]


class AccountsPool:
    # _order_by: str = "RANDOM()"
    _order_by: str = "username"

    def __init__(
        self,
        login_config: LoginConfig | None = None,
        raise_when_no_account=False,
    ):
        self._login_config = login_config or LoginConfig()
        self._raise_when_no_account = raise_when_no_account

    async def load_from_file(self, filepath: str, line_format: str):
        line_delim = guess_delim(line_format)
        tokens = line_format.split(line_delim)

        required = set(["username", "password", "email", "email_password"])
        if not required.issubset(tokens):
            raise ValueError(f"Invalid line format: {line_format}")

        accounts = []
        with open(filepath, "r") as f:
            lines = f.read().split("\n")
            lines = [x.strip() for x in lines if x.strip()]

            for line in lines:
                data = [x.strip() for x in line.split(line_delim)]
                if len(data) < len(tokens):
                    raise ValueError(f"Invalid line: {line}")

                data = data[: len(tokens)]
                vals = {k: v for k, v in zip(tokens, data) if k != "_"}
                accounts.append(vals)

        for x in accounts:
            await self.add_account(**x)

    async def add_account(
        self,
        username: str,
        password: str,
        email: str,
        email_password: str,
        user_agent: str | None = None,
        proxy: str | None = None,
        cookies: str | None = None,
        mfa_code: str | None = None,
    ):
        qs = "SELECT * FROM accounts WHERE username = :username"
        rs = await fetchone(qs, {"username": username})
        if rs:
            logger.warning(f"Account {username} already exists")
            return

        account = Account(
            username=username,
            password=password,
            email=email,
            email_password=email_password,
            user_agent=user_agent or UserAgent().safari,
            active=False,
            locks={},
            stats={},
            headers={},
            cookies=parse_cookies(cookies) if cookies else {},
            proxy=proxy,
            mfa_code=mfa_code,
        )

        if proxy:
            from twscrape.proxies import ensure

            await ensure(proxy)

        if "ct0" in account.cookies:
            account.active = True

        await self.save(account)
        logger.info(f"Account {username} added successfully (active={account.active})")

    async def delete_accounts(self, usernames: str | list[str]):
        usernames = usernames if isinstance(usernames, list) else [usernames]
        usernames = list(set(usernames))
        if not usernames:
            logger.warning("No usernames provided")
            return

        # Use parameterized query to avoid SQL injection and quote issues
        placeholders = ",".join([f":username_{i}" for i in range(len(usernames))])
        params = {f"username_{i}": username for i, username in enumerate(usernames)}
        qs = f"DELETE FROM accounts WHERE username IN ({placeholders})"
        await execute(qs, params)

    async def delete_inactive(self):
        qs = "DELETE FROM accounts WHERE active = false"
        await execute(qs)

    async def get(self, username: str):
        qs = "SELECT * FROM accounts WHERE username = :username"
        rs = await fetchone(qs, {"username": username})
        if not rs:
            raise ValueError(f"Account {username} not found")
        return Account.from_rs(rs)

    async def get_all(self):
        qs = "SELECT * FROM accounts"
        rs = await fetchall(qs)
        return [Account.from_rs(x) for x in rs]

    async def get_account(self, username: str):
        qs = "SELECT * FROM accounts WHERE username = :username"
        rs = await fetchone(qs, {"username": username})
        if not rs:
            return None
        return Account.from_rs(rs)

    async def save(self, account: Account):
        data = account.to_rs()
        cols = list(data.keys())

        qs = f"""
        INSERT INTO accounts ({",".join(cols)}) VALUES ({",".join([f":{x}" for x in cols])})
        ON CONFLICT(username) DO UPDATE SET {",".join([f"{x}=excluded.{x}" for x in cols])}
        """
        await execute(qs, data)

    async def login(self, account: Account):
        try:
            await login(account, cfg=self._login_config)
            logger.info(f"Logged in to {account.username} successfully")
            return True
        except HTTPStatusError as e:
            rep = e.response
            logger.error(f"Failed to login '{account.username}': {rep.status_code} - {rep.text}")
            return False
        except Exception as e:
            logger.error(f"Failed to login '{account.username}': {e}")
            return False
        finally:
            await self.save(account)

    async def login_all(self, usernames: list[str] | None = None):
        if usernames is None:
            qs = "SELECT * FROM accounts WHERE active = false AND error_msg IS NULL"
            rs = await fetchall(qs)
        else:
            # Use parameterized query
            placeholders = ",".join([f":username_{i}" for i in range(len(usernames))])
            params = {f"username_{i}": username for i, username in enumerate(usernames)}
            qs = f"SELECT * FROM accounts WHERE username IN ({placeholders})"
            rs = await fetchall(qs, params)

        accounts = [Account.from_rs(rs) for rs in rs]
        # await asyncio.gather(*[login(x) for x in self.accounts])

        counter = {"total": len(accounts), "success": 0, "failed": 0}
        for i, x in enumerate(accounts, start=1):
            logger.info(f"[{i}/{len(accounts)}] Logging in {x.username} - {x.email}")
            status = await self.login(x)
            counter["success" if status else "failed"] += 1
        return counter

    async def relogin(self, usernames: str | list[str]):
        usernames = usernames if isinstance(usernames, list) else [usernames]
        usernames = list(set(usernames))
        if not usernames:
            logger.warning("No usernames provided")
            return

        # Use parameterized query
        placeholders = ",".join([f":username_{i}" for i in range(len(usernames))])
        params = {f"username_{i}": username for i, username in enumerate(usernames)}
        qs = f"""
        UPDATE accounts SET
            active = false,
            locks = '{{}}'::jsonb,
            last_used = NULL,
            error_msg = NULL,
            headers = '{{}}'::jsonb,
            cookies = '{{}}'::jsonb,
            user_agent = "{UserAgent().safari}"
        WHERE username IN ({placeholders})
        """

        await execute(qs, params)
        await self.login_all(usernames)

    async def relogin_failed(self):
        qs = "SELECT username FROM accounts WHERE active = false AND error_msg IS NOT NULL"
        rs = await fetchall(qs)
        await self.relogin([x["username"] for x in rs])

    async def reset_locks(self):
        qs = "UPDATE accounts SET locks = '{{}}'::jsonb"
        await execute(qs)

    async def set_active(self, username: str, active: bool):
        qs = "UPDATE accounts SET active = :active WHERE username = :username"
        await execute(qs, {"username": username, "active": active})

    async def lock_until(self, username: str, queue: str, unlock_at: int, req_count=0):
        qs = f"""
        UPDATE accounts SET
            locks = jsonb_set(
                locks,
                '{{{queue}}}',
                to_jsonb(to_timestamp({unlock_at})::text),
                true
            ),
            stats = jsonb_set(
                stats,
                '{{{queue}}}',
                to_jsonb(COALESCE((stats->>'{queue}')::int, 0) + {req_count}),
                true
            ),
            last_used = now()
        WHERE username = :username
        """
        await execute(qs, {"username": username})

    async def unlock(self, username: str, queue: str, req_count=0):
        # Remove the lock and update timestamp - simplified version
        qs = """
        UPDATE accounts SET
            locks = locks - :queue_name,
            last_used = now()
        WHERE username = :username
        """
        await execute(qs, {"username": username, "queue_name": queue})

        # Update stats separately if req_count > 0
        if req_count > 0:
            stats_qs = f"""
            UPDATE accounts SET
                stats = jsonb_set(
                    stats,
                    '{{{queue}}}',
                    to_jsonb(COALESCE((stats->>'{queue}')::int, 0) + {req_count}),
                    true
                )
            WHERE username = :username
            """
            await execute(stats_qs, {"username": username})

    async def _get_and_lock(self, queue: str, condition: str):
        # if space in condition, it's a sub‑query, otherwise it's a literal username
        condition = f"({condition})" if " " in condition else f"'{condition}'"

        qs = f"""
        UPDATE accounts
        SET
            locks = jsonb_set(
                locks,
                '{{{queue}}}',
                to_jsonb((now() + interval '15 minutes')::text),
                true
            ),
            last_used = now()
        WHERE username = {condition}
        RETURNING *
        """
        rs = await fetchone(qs)
        return Account.from_rs(rs) if rs else None

    async def get_for_queue(self, queue: str):
        q = f"""
        SELECT username FROM accounts
        WHERE active = true AND (
            locks->>'{queue}' IS NULL
            OR (locks->>'{queue}')::timestamptz < now()
        )
        ORDER BY {self._order_by}
        LIMIT 1
        """

        return await self._get_and_lock(queue, q)

    async def get_for_queue_or_wait(self, queue: str) -> Account | None:
        msg_shown = False
        while True:
            account = await self.get_for_queue(queue)
            if not account:
                if self._raise_when_no_account or get_env_bool("TWS_RAISE_WHEN_NO_ACCOUNT"):
                    raise NoAccountError(f"No account available for queue {queue}")

                if not msg_shown:
                    nat = await self.next_available_at(queue)
                    if not nat:
                        logger.warning("No active accounts. Stopping...")
                        return None

                    msg = f'No account available for queue "{queue}". Next available at {nat}'
                    logger.info(msg)
                    msg_shown = True

                await asyncio.sleep(5)
                continue
            else:
                if msg_shown:
                    logger.info(f"Continuing with account {account.username} on queue {queue}")

            return account

    async def next_available_at(self, queue: str):
        qs = f"""
        SELECT (locks->>'{queue}')::timestamptz AS lock_until
        FROM accounts
        WHERE active = true AND locks->>'{queue}' IS NOT NULL
        ORDER BY lock_until ASC
        LIMIT 1
        """
        rs = await fetchone(qs)
        if rs:
            now, trg = utc.now(), utc.from_iso(rs[0])
            if trg < now:
                return "now"

            at_local = datetime.now() + (trg - now)
            return at_local.strftime("%H:%M:%S")

        return None

    async def mark_inactive(self, username: str, error_msg: str | None):
        qs = """
        UPDATE accounts SET active = false, error_msg = :error_msg
        WHERE username = :username
        """
        await execute(qs, {"username": username, "error_msg": error_msg})

    async def stats(self):
        def locks_count(queue: str):
            return f"""
            SELECT COUNT(*) FROM accounts
            WHERE (locks->>'{queue}')::timestamptz IS NOT NULL
              AND (locks->>'{queue}')::timestamptz > now()
            """

        qs = "SELECT DISTINCT f.key AS k FROM accounts, jsonb_each(locks) AS f(key, value)"
        rs = await fetchall(qs)
        gql_ops = [dict(x._mapping)["k"] if hasattr(x, "_mapping") else x[0] for x in rs]

        config = [
            ("total", "SELECT COUNT(*) FROM accounts"),
            ("active", "SELECT COUNT(*) FROM accounts WHERE active = true"),
            ("inactive", "SELECT COUNT(*) FROM accounts WHERE active = false"),
            *[(f"locked_{x}", locks_count(x)) for x in gql_ops],
        ]

        quote = '"'
        qs = f"SELECT {','.join([f'({q}) as {quote}{k}{quote}' for k, q in config])}"
        rs = await fetchone(qs)
        return dict(rs._mapping) if rs else {}

    async def accounts_info(self):
        accounts = await self.get_all()

        items: list[AccountInfo] = []
        for x in accounts:
            item: AccountInfo = {
                "username": x.username,
                "logged_in": (x.headers or {}).get("authorization", "") != "",
                "active": x.active,
                "last_used": x.last_used,
                "total_req": sum(x.stats.values()),
                "error_msg": str(x.error_msg)[0:60],
            }
            items.append(item)

        old_time = datetime(1970, 1, 1).replace(tzinfo=timezone.utc)
        items = sorted(items, key=lambda x: x["username"].lower())
        items = sorted(
            items,
            key=lambda x: x["last_used"] or old_time if x["total_req"] > 0 else old_time,
            reverse=True,
        )
        items = sorted(items, key=lambda x: x["active"], reverse=True)
        # items = sorted(items, key=lambda x: x["total_req"], reverse=True)
        return items
