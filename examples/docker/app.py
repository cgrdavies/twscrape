#!/usr/bin/env python3
"""
Example application showing how to use twscrape with database migrations.

This example demonstrates:
1. Checking migration status programmatically
2. Using the AccountsPool and API
3. Proper async setup
"""

import asyncio
import os
import sys

# Add the project root to the path
sys.path.insert(0, '/app')

import twscrape
from twscrape import AccountsPool, API


async def main():
    print("🚀 Starting twscrape example application")

    # Check migration status (optional - migrations should already be done by init container)
    print("🔍 Checking database migration status...")
    status = twscrape.check_migration_status()

    if "error" in status:
        print(f"❌ Database error: {status['error']}")
        sys.exit(1)

    if status.get('needs_migration'):
        print("⚠️  Database needs migrations - this should have been handled by init container")
        print("🔄 Running migrations...")
        success = twscrape.init_database()
        if not success:
            print("❌ Migration failed")
            sys.exit(1)
    else:
        print("✅ Database is up to date")

    # Initialize the accounts pool and API
    print("🔧 Initializing twscrape...")
    pool = AccountsPool()
    api = API(pool)

    # Check account status
    print("👥 Checking accounts...")
    accounts = await pool.accounts_info()
    print(f"📊 Found {len(accounts)} accounts")

    if len(accounts) == 0:
        print("⚠️  No accounts configured. Add accounts using:")
        print("   twscrape add_accounts accounts.txt username:password:email:email_password")
        print("   twscrape login_accounts")
    else:
        # Show account stats
        stats = await pool.stats()
        print(f"📈 Account stats: {stats}")

        # Example: Search for tweets (if accounts are available and active)
        if stats.get('active', 0) > 0:
            print("🔍 Testing search functionality...")
            try:
                tweets = []
                async for tweet in api.search("python", limit=5):
                    tweets.append(tweet)
                print(f"✅ Successfully retrieved {len(tweets)} tweets")
            except Exception as e:
                print(f"⚠️  Search failed (this is normal if no accounts are logged in): {e}")

    print("✅ Application startup complete")

    # Keep the application running
    print("🔄 Application running... (Press Ctrl+C to stop)")
    try:
        while True:
            await asyncio.sleep(60)
            print("💓 Application heartbeat")
    except KeyboardInterrupt:
        print("🛑 Application stopped")


if __name__ == "__main__":
    asyncio.run(main())
