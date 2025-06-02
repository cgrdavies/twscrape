import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime

from httpx import AsyncClient, AsyncHTTPTransport

from .models import JSONTrait
from .utils import utc

TOKEN = "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"


@dataclass
class Account(JSONTrait):
    username: str
    password: str
    email: str
    email_password: str
    user_agent: str
    active: bool
    locks: dict[str, datetime] = field(default_factory=dict)  # queue: datetime
    stats: dict[str, int] = field(default_factory=dict)  # queue: requests
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    mfa_code: str | None = None
    proxy: str | None = None
    error_msg: str | None = None
    last_used: datetime | None = None
    _tx: str | None = None

    @staticmethod
    def from_rs(rs):
        """Create Account from SQLAlchemy Row object."""
        doc = dict(rs._mapping)

        # Handle JSONB fields - PostgreSQL returns them as dict objects, not strings
        locks_data = doc["locks"] if isinstance(doc["locks"], dict) else json.loads(doc["locks"])
        doc["locks"] = {k: utc.from_iso(v) if isinstance(v, str) else v for k, v in locks_data.items()}

        stats_data = doc["stats"] if isinstance(doc["stats"], dict) else json.loads(doc["stats"])
        doc["stats"] = {k: v for k, v in stats_data.items() if isinstance(v, int)}

        headers_data = doc["headers"] if isinstance(doc["headers"], dict) else json.loads(doc["headers"])
        doc["headers"] = headers_data

        cookies_data = doc["cookies"] if isinstance(doc["cookies"], dict) else json.loads(doc["cookies"])
        doc["cookies"] = cookies_data

        doc["active"] = bool(doc["active"])

        # Handle last_used - PostgreSQL returns datetime objects, SQLite returned strings
        if doc["last_used"]:
            if isinstance(doc["last_used"], str):
                doc["last_used"] = utc.from_iso(doc["last_used"])
            # If it's already a datetime object (PostgreSQL), keep as is
        else:
            doc["last_used"] = None

        # Map tx column to _tx field
        if "tx" in doc:
            doc["_tx"] = doc.pop("tx")

        return Account(**doc)

    def to_rs(self):
        rs = asdict(self)
        rs["locks"] = json.dumps(rs["locks"], default=lambda x: x.isoformat())
        rs["stats"] = json.dumps(rs["stats"])
        rs["headers"] = json.dumps(rs["headers"])
        rs["cookies"] = json.dumps(rs["cookies"])
        rs["last_used"] = rs["last_used"].isoformat() if rs["last_used"] else None

        # Map _tx field to tx column
        if "_tx" in rs:
            rs["tx"] = rs.pop("_tx")

        return rs

    def make_client(self, proxy: str | None = None) -> AsyncClient:
        proxies = [proxy, os.getenv("TWS_PROXY"), self.proxy]
        proxies = [x for x in proxies if x is not None]
        proxy = proxies[0] if proxies else None

        transport = AsyncHTTPTransport(retries=3)
        client = AsyncClient(proxy=proxy, follow_redirects=True, transport=transport)

        # saved from previous usage
        client.cookies.update(self.cookies)
        client.headers.update(self.headers)

        # default settings
        client.headers["user-agent"] = self.user_agent
        client.headers["content-type"] = "application/json"
        client.headers["authorization"] = TOKEN
        client.headers["x-twitter-active-user"] = "yes"
        client.headers["x-twitter-client-language"] = "en"

        if "ct0" in client.cookies:
            client.headers["x-csrf-token"] = client.cookies["ct0"]

        return client
