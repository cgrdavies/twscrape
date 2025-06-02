#!/usr/bin/env python3
"""
Example: Using twscrape with PostgreSQL database

twscrape now uses PostgreSQL as its primary database backend.
This example shows the different ways to configure the database connection.

Prerequisites:
1. PostgreSQL server running
2. Database created (e.g., CREATE DATABASE twscrape;)
3. Run migrations: alembic upgrade head
"""

import asyncio

from twscrape import API


async def main():
    # Option 1: Configure database URL directly in API constructor
    api = API(database_url="postgresql+asyncpg://user:password@localhost:5432/twscrape")

    # Option 2: Use environment variable (recommended for production)
    # Set TWSCRAPE_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/twscrape
    # api = API()

    # Option 3: Use .env file (for development)
    # Create .env file with: TWSCRAPE_DATABASE_URL=postgresql+asyncpg://...
    # api = API()

    # NOTE: If you get a MigrationError, run:
    # alembic upgrade head
    # (or with custom DB URL: TWSCRAPE_DATABASE_URL='...' alembic upgrade head)

    try:
        # Test the connection - this will check for migrations automatically
        stats = await api.pool.stats()
        print(f"✅ Connected to PostgreSQL! Stats: {stats}")

        # Add accounts
        # await api.pool.add_account("user1", "pass1", "email1@example.com", "email_pass1")

        # Use the API normally
        # tweets = await gather(api.search("python", limit=5))
        # print(f"Found {len(tweets)} tweets")

    except Exception as e:
        print(f"❌ Error: {e}")
        if "MigrationError" in str(type(e)):
            print("💡 Run 'alembic upgrade head' to set up the database schema")


if __name__ == "__main__":
    asyncio.run(main())
