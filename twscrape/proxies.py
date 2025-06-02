from datetime import datetime

from .db_pg import execute, fetchone, fetchall


async def ensure(url: str):
    await execute(
        """INSERT INTO proxies (url) VALUES (:url)
           ON CONFLICT (url) DO NOTHING""",
        {"url": url},
    )


async def get_active() -> str | None:
    row = await fetchone("SELECT url FROM proxies WHERE active = true ORDER BY random() LIMIT 1")
    return row[0] if row else None


async def mark_failed(url: str):
    await execute(
        """UPDATE proxies
              SET active = false,
                  fail_count = fail_count + 1,
                  last_failed = :ts
            WHERE url = :url""",
        {"url": url, "ts": datetime.utcnow()},
    )
