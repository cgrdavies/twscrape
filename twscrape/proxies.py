from datetime import datetime

from .db_pg import execute, fetchone, fetchall


async def ensure(url: str):
    await execute(
        """INSERT INTO proxies (url) VALUES (:url)
           ON CONFLICT (url) DO NOTHING""",
        {"url": url},
    )


async def get_active() -> tuple[int, str] | None:
    row = await fetchone(
        "SELECT id, url FROM proxies WHERE active = true ORDER BY random() LIMIT 1"
    )
    return (row[0], row[1]) if row else None


async def get_url(proxy_id: int) -> str | None:
    row = await fetchone("SELECT url FROM proxies WHERE id = :id", {"id": proxy_id})
    return row[0] if row else None


async def get_proxy_id(url: str) -> int | None:
    row = await fetchone("SELECT id FROM proxies WHERE url = :url", {"url": url})
    return row[0] if row else None


async def mark_failed(proxy_id: int):
    await execute(
        """UPDATE proxies
              SET active = false,
                  fail_count = fail_count + 1,
                  last_failed = :ts
            WHERE id = :id""",
        {"id": proxy_id, "ts": datetime.utcnow()},
    )
