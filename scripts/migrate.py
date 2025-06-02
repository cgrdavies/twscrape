#!/usr/bin/env python3
"""
Standalone migration script for Docker containers.

This script can be used to run database migrations in containerized environments
where you want to ensure the database is properly set up before starting the main application.

Usage:
    python scripts/migrate.py [--check-only] [--wait-for-db]

Environment Variables:
    TWSCRAPE_DATABASE_URL: PostgreSQL connection string
    TWSCRAPE_DB_WAIT_TIMEOUT: Seconds to wait for database (default: 30)
"""

import argparse
import sys
import time
from pathlib import Path

# Add the parent directory to the path so we can import twscrape
sys.path.insert(0, str(Path(__file__).parent.parent))

from twscrape.config import get_database_url
from twscrape.migrations.utils import check_migration_status, init_database


def wait_for_database(timeout: int = 30) -> bool:
    """
    Wait for the database to become available.

    Args:
        timeout: Maximum seconds to wait

    Returns:
        bool: True if database is available, False if timeout
    """
    print(f"🔄 Waiting for database to become available (timeout: {timeout}s)...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            status = check_migration_status()
            if "error" not in status:
                print("✅ Database is available")
                return True
            else:
                print(f"⏳ Database not ready: {status['error']}")
        except Exception as e:
            print(f"⏳ Database not ready: {e}")

        time.sleep(2)

    print(f"❌ Database did not become available within {timeout} seconds")
    return False


def main():
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check migration status, don't run migrations",
    )
    parser.add_argument(
        "--wait-for-db",
        action="store_true",
        help="Wait for database to become available before proceeding",
    )
    parser.add_argument(
        "--timeout", type=int, default=30, help="Database wait timeout in seconds (default: 30)"
    )

    args = parser.parse_args()

    # Check if database URL is configured
    try:
        db_url = get_database_url()
        print(f"📊 Database URL: {db_url.split('@')[1] if '@' in db_url else db_url}")
    except Exception as e:
        print(f"❌ Failed to get database URL: {e}")
        print("💡 Make sure TWSCRAPE_DATABASE_URL environment variable is set")
        sys.exit(1)

    # Wait for database if requested
    if args.wait_for_db:
        if not wait_for_database(args.timeout):
            sys.exit(1)

    # Check migration status
    print("🔍 Checking migration status...")
    status = check_migration_status()

    if "error" in status:
        print(f"❌ Migration status check failed: {status['error']}")
        sys.exit(1)

    print("📊 Migration Status:")
    print(f"   Current revision: {status.get('current_revision', 'None')}")
    print(f"   Head revision: {status.get('head_revision', 'None')}")
    print(f"   Up to date: {'✅' if status.get('is_up_to_date') else '❌'}")
    print(f"   Needs migration: {'❌' if status.get('needs_migration') else '✅'}")

    if args.check_only:
        # Exit with non-zero code if migrations are needed
        sys.exit(0 if not status.get("needs_migration", True) else 1)

    # Run migrations if needed
    if status.get("needs_migration", True):
        print("🔄 Running database migrations...")
        success = init_database()
        if success:
            print("✅ Database migrations completed successfully")
            sys.exit(0)
        else:
            print("❌ Database migrations failed")
            sys.exit(1)
    else:
        print("✅ Database is already up to date")
        sys.exit(0)


if __name__ == "__main__":
    main()
