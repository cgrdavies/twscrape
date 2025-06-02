#!/bin/bash
set -e  # Exit on any error

echo "🚀 Setting up twscrape development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to install and setup PostgreSQL
install_postgresql() {
    print_status "Installing PostgreSQL..."

    # Update package index
    sudo apt-get update

    # Install PostgreSQL
    sudo apt-get install -y postgresql postgresql-contrib

    print_success "PostgreSQL installed"

    # Check if systemd is available
    if command -v systemctl &> /dev/null && systemctl is-system-running &>/dev/null; then
        print_status "Using systemd to manage PostgreSQL..."
        # Start and enable PostgreSQL service
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
    else
        print_status "Systemd not available, starting PostgreSQL manually..."
        # Start PostgreSQL manually
        sudo -u postgres /usr/lib/postgresql/*/bin/pg_ctl -D /var/lib/postgresql/*/main -l /var/lib/postgresql/*/main/pg.log start || true

        # Alternative: use service command if available
        if command -v service &> /dev/null; then
            sudo service postgresql start || true
        fi

        # Give PostgreSQL a moment to start
        sleep 3
    fi

    print_success "PostgreSQL started"

    # Setup database and user
    print_status "Setting up PostgreSQL database and user..."

    # Wait for PostgreSQL to be ready
    max_attempts=10
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if sudo -u postgres psql -c "SELECT 1;" &>/dev/null; then
            break
        fi

        if [ $attempt -eq $max_attempts ]; then
            print_error "PostgreSQL failed to start properly"
            exit 1
        fi

        print_status "Waiting for PostgreSQL to be ready... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done

    # Create database and user
    sudo -u postgres psql -c "CREATE DATABASE twscrape;" 2>/dev/null || print_warning "Database 'twscrape' may already exist"
    sudo -u postgres psql -c "CREATE USER twscrape_user WITH PASSWORD 'twscrape_pass';" 2>/dev/null || print_warning "User 'twscrape_user' may already exist"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE twscrape TO twscrape_user;" 2>/dev/null || true
    sudo -u postgres psql -c "ALTER USER twscrape_user CREATEDB;" 2>/dev/null || true

    # Grant schema permissions (important for newer PostgreSQL versions)
    sudo -u postgres psql -d twscrape -c "GRANT ALL ON SCHEMA public TO twscrape_user;" 2>/dev/null || true
    sudo -u postgres psql -d twscrape -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO twscrape_user;" 2>/dev/null || true
    sudo -u postgres psql -d twscrape -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO twscrape_user;" 2>/dev/null || true
    sudo -u postgres psql -d twscrape -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO twscrape_user;" 2>/dev/null || true
    sudo -u postgres psql -d twscrape -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO twscrape_user;" 2>/dev/null || true

    # Make the user owner of the database for full control
    sudo -u postgres psql -c "ALTER DATABASE twscrape OWNER TO twscrape_user;" 2>/dev/null || true

    print_success "PostgreSQL database and user configured"
}

# Function to start PostgreSQL if it's not running
start_postgresql() {
    if command -v systemctl &> /dev/null && systemctl is-system-running &>/dev/null; then
        if ! sudo systemctl is-active --quiet postgresql; then
            print_status "Starting PostgreSQL service..."
            sudo systemctl start postgresql
        fi
    else
        # Check if PostgreSQL is running by trying to connect
        if ! sudo -u postgres psql -c "SELECT 1;" &>/dev/null; then
            print_status "Starting PostgreSQL manually..."

            # Try different methods to start PostgreSQL
            sudo -u postgres /usr/lib/postgresql/*/bin/pg_ctl -D /var/lib/postgresql/*/main -l /var/lib/postgresql/*/main/pg.log start || true

            if command -v service &> /dev/null; then
                sudo service postgresql start || true
            fi

            # Give it time to start
            sleep 3
        fi
    fi
}

# Check if PostgreSQL is installed, install if not
print_status "Checking PostgreSQL installation..."
if ! command -v psql &> /dev/null; then
    print_warning "PostgreSQL is not installed. Installing PostgreSQL..."
    install_postgresql
else
    print_success "PostgreSQL is already installed"

    # Start PostgreSQL if needed
    start_postgresql

    # Ensure database and user exist
    print_status "Ensuring database and user exist..."

    # Wait for PostgreSQL to be ready
    max_attempts=10
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if sudo -u postgres psql -c "SELECT 1;" &>/dev/null; then
            break
        fi

        if [ $attempt -eq $max_attempts ]; then
            print_error "PostgreSQL is not responding"
            exit 1
        fi

        print_status "Waiting for PostgreSQL... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done

    sudo -u postgres psql -c "CREATE DATABASE twscrape;" 2>/dev/null || print_warning "Database 'twscrape' may already exist"
    sudo -u postgres psql -c "CREATE USER twscrape_user WITH PASSWORD 'twscrape_pass';" 2>/dev/null || print_warning "User 'twscrape_user' may already exist"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE twscrape TO twscrape_user;" 2>/dev/null || true
    sudo -u postgres psql -c "ALTER USER twscrape_user CREATEDB;" 2>/dev/null || true

    # Grant schema permissions (important for newer PostgreSQL versions)
    sudo -u postgres psql -d twscrape -c "GRANT ALL ON SCHEMA public TO twscrape_user;" 2>/dev/null || true
    sudo -u postgres psql -d twscrape -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO twscrape_user;" 2>/dev/null || true
    sudo -u postgres psql -d twscrape -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO twscrape_user;" 2>/dev/null || true
    sudo -u postgres psql -d twscrape -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO twscrape_user;" 2>/dev/null || true
    sudo -u postgres psql -d twscrape -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO twscrape_user;" 2>/dev/null || true

    # Make the user owner of the database for full control
    sudo -u postgres psql -c "ALTER DATABASE twscrape OWNER TO twscrape_user;" 2>/dev/null || true
fi

print_success "PostgreSQL is ready"

# Check if Python 3.10+ is available
print_status "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.10 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_VERSION="3.10"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
    print_error "Python $PYTHON_VERSION found, but Python 3.10+ is required."
    exit 1
fi

print_success "Python $PYTHON_VERSION is compatible"

# Create virtual environment
print_status "Creating Python virtual environment..."
if [ -d ".venv" ]; then
    print_warning "Virtual environment already exists. Removing and recreating..."
    rm -rf .venv
fi

python3 -m venv .venv
print_success "Virtual environment created"

# Activate virtual environment
print_status "Activating virtual environment..."
source .venv/bin/activate
print_success "Virtual environment activated"

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install project dependencies
print_status "Installing project dependencies..."
if [ -f "Makefile" ]; then
    print_status "Using Makefile for installation..."
    make install
else
    print_status "Installing main dependencies and dev dependencies..."
    # Install main dependencies first
    pip install -e .
    # Then install with dev dependencies
    pip install -e .[dev]
fi
print_success "Dependencies installed"

# Verify key dependencies are installed
print_status "Verifying key dependencies..."
python -c "import httpx; print(f'✅ httpx {httpx.__version__} installed')" 2>/dev/null || print_warning "httpx not found"
python -c "import asyncpg; print(f'✅ asyncpg version installed')" 2>/dev/null || print_warning "asyncpg not found"
python -c "import alembic; print(f'✅ alembic version installed')" 2>/dev/null || print_warning "alembic not found"

# Set environment variables
print_status "Setting environment variables..."
export TWSCRAPE_DATABASE_URL="postgresql+asyncpg://twscrape_user:twscrape_pass@localhost:5432/twscrape"

# Create .env file for persistent environment variables
echo "TWSCRAPE_DATABASE_URL=postgresql+asyncpg://twscrape_user:twscrape_pass@localhost:5432/twscrape" > .env
print_success "Environment variables set and saved to .env file"

# Run database migrations
print_status "Running database migrations..."
if command -v alembic &> /dev/null; then
    alembic upgrade head
    print_success "Database migrations completed"
else
    print_warning "Alembic not found in PATH, trying with python -m"
    python -m alembic upgrade head
    print_success "Database migrations completed"
fi

# Verify installation
print_status "Verifying installation..."
if python -c "import twscrape; print('✅ twscrape imported successfully')" 2>/dev/null; then
    print_success "Installation verified successfully"
else
    print_error "Installation verification failed"
    exit 1
fi

# Check if twscrape CLI is working
print_status "Testing twscrape CLI..."
if twscrape --help &>/dev/null; then
    print_success "twscrape CLI is working"
else
    print_warning "twscrape CLI test failed, but this might be normal"
fi

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Activate the virtual environment: ${YELLOW}source .venv/bin/activate${NC}"
echo "2. Add Twitter accounts: ${YELLOW}twscrape add_accounts accounts.txt username:password:email:email_password${NC}"
echo "3. Login accounts: ${YELLOW}twscrape login_accounts${NC}"
echo "4. Start scraping: ${YELLOW}twscrape search 'your query' --limit 10${NC}"
echo ""
echo -e "${GREEN}Development commands:${NC}"
echo "• Run tests: ${YELLOW}make test${NC}"
echo "• Run linting: ${YELLOW}make lint${NC}"
echo "• Check everything: ${YELLOW}make check${NC}"
echo ""
echo -e "${GREEN}PostgreSQL (Local):${NC}"
if command -v systemctl &> /dev/null && systemctl is-system-running &>/dev/null; then
    echo "• Service status: ${YELLOW}sudo systemctl status postgresql${NC}"
    echo "• Stop service: ${YELLOW}sudo systemctl stop postgresql${NC}"
    echo "• Start service: ${YELLOW}sudo systemctl start postgresql${NC}"
else
    echo "• Check if running: ${YELLOW}sudo -u postgres psql -c 'SELECT 1;'${NC}"
    echo "• Start manually: ${YELLOW}sudo service postgresql start${NC} (or use pg_ctl)"
    echo "• Stop manually: ${YELLOW}sudo service postgresql stop${NC} (or use pg_ctl)"
fi
echo "• Connect to database: ${YELLOW}psql -h localhost -U twscrape_user -d twscrape${NC}"
echo ""
echo -e "${GREEN}Environment:${NC}"
echo "• Database URL: ${YELLOW}$TWSCRAPE_DATABASE_URL${NC}"
echo "• Virtual environment: ${YELLOW}.venv${NC}"
echo "• Environment file: ${YELLOW}.env${NC}"
