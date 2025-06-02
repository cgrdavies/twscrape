#!/bin/bash

# Set the database URL for twscrape to use PostgreSQL
export TWSCRAPE_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/twscrape"

echo "✅ Database environment variable set:"
echo "TWSCRAPE_DATABASE_URL=$TWSCRAPE_DATABASE_URL"
echo ""
echo "You can now run twscrape commands like:"
echo "  alembic upgrade head"
echo "  twscrape accounts"
echo "  twscrape add_accounts accounts.txt"
echo ""
echo "To make this permanent, add the export line to your ~/.bashrc or ~/.zshrc"
