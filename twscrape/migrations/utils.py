"""
Migration utilities for programmatic database schema management.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from ..config import get_database_url


def get_alembic_config() -> Config:
    """Get Alembic configuration with proper paths."""
    # Get the migrations directory (this file's parent)
    migrations_dir = Path(__file__).parent

    # Create Alembic config
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", str(migrations_dir))

    # Convert async URL to sync for Alembic
    db_url = get_database_url()
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    return alembic_cfg


def get_sync_engine():
    """Get synchronous SQLAlchemy engine for migrations."""
    db_url = get_database_url()
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    return create_engine(db_url)


def check_migration_status() -> dict:
    """
    Check the current migration status.

    Returns:
        dict: Migration status information
    """
    try:
        alembic_cfg = get_alembic_config()

        # Get current revision from database
        engine = get_sync_engine()
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()

        # Get head revision from scripts
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        head_rev = script_dir.get_current_head()

        # Check if migrations table exists
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'alembic_version'
                )
            """))
            has_alembic_table = result.scalar()

        return {
            "current_revision": current_rev,
            "head_revision": head_rev,
            "is_up_to_date": current_rev == head_rev,
            "has_alembic_table": has_alembic_table,
            "needs_migration": current_rev != head_rev or not has_alembic_table
        }

    except Exception as e:
        return {
            "error": str(e),
            "needs_migration": True
        }


def run_migrations(target_revision: str = "head") -> bool:
    """
    Run database migrations programmatically.

    Args:
        target_revision: Target revision (default: "head" for latest)

    Returns:
        bool: True if successful
    """
    try:
        alembic_cfg = get_alembic_config()

        # Run the migration
        command.upgrade(alembic_cfg, target_revision)

        print(f"✅ Migrations completed successfully to revision: {target_revision}")
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


def create_migration(message: str, autogenerate: bool = True) -> bool:
    """
    Create a new migration file.

    Args:
        message: Migration description
        autogenerate: Whether to auto-generate migration from model changes

    Returns:
        bool: True if successful
    """
    try:
        alembic_cfg = get_alembic_config()

        # Create the migration
        command.revision(
            alembic_cfg,
            message=message,
            autogenerate=autogenerate
        )

        print(f"✅ Migration created: {message}")
        return True

    except Exception as e:
        print(f"❌ Migration creation failed: {e}")
        return False


def get_migration_history() -> List[dict]:
    """Get migration history."""
    try:
        alembic_cfg = get_alembic_config()
        script_dir = ScriptDirectory.from_config(alembic_cfg)

        history = []
        for rev in script_dir.walk_revisions():
            history.append({
                "revision": rev.revision,
                "down_revision": rev.down_revision,
                "description": rev.doc,
                "branch_labels": rev.branch_labels,
            })

        return history

    except Exception as e:
        print(f"❌ Failed to get migration history: {e}")
        return []


def init_database() -> bool:
    """
    Initialize database with current schema.
    This is equivalent to running all migrations on a fresh database.
    """
    try:
        status = check_migration_status()

        if status.get("error"):
            print(f"❌ Database connection failed: {status['error']}")
            return False

        if not status.get("needs_migration", True):
            print("✅ Database is already up to date")
            return True

        print("🔄 Running database migrations...")
        return run_migrations()

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
