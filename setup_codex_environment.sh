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

# Check if Docker is installed and running
print_status "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! docker info &> /dev/null; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

print_success "Docker is available and running"

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
    print_status "Installing manually..."
    pip install -e .[dev]
fi
print_success "Dependencies installed"

# Start PostgreSQL Docker container
print_status "Starting PostgreSQL Docker container..."

# Stop and remove existing container if it exists
if docker ps -a --format 'table {{.Names}}' | grep -q "twscrape-postgres"; then
    print_warning "Existing PostgreSQL container found. Stopping and removing..."
    docker stop twscrape-postgres 2>/dev/null || true
    docker rm twscrape-postgres 2>/dev/null || true
fi

# Start new PostgreSQL container
print_status "Starting new PostgreSQL container..."
docker run -d \
    --name twscrape-postgres \
    -e POSTGRES_DB=twscrape \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -p 5432:5432 \
    --restart unless-stopped \
    postgres:15

print_success "PostgreSQL container started"

# Wait for PostgreSQL to be ready
print_status "Waiting for PostgreSQL to be ready..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if docker exec twscrape-postgres pg_isready -U postgres -d twscrape &>/dev/null; then
        break
    fi

    if [ $attempt -eq $max_attempts ]; then
        print_error "PostgreSQL failed to start within ${max_attempts} seconds"
        docker logs twscrape-postgres
        exit 1
    fi

    print_status "Waiting for PostgreSQL... (attempt $attempt/$max_attempts)"
    sleep 2
    ((attempt++))
done

print_success "PostgreSQL is ready"

# Set environment variables
print_status "Setting environment variables..."
export TWSCRAPE_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/twscrape"

# Create .env file for persistent environment variables
echo "TWSCRAPE_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/twscrape" > .env
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
echo -e "${GREEN}Docker PostgreSQL:${NC}"
echo "• Container name: ${YELLOW}twscrape-postgres${NC}"
echo "• Stop container: ${YELLOW}docker stop twscrape-postgres${NC}"
echo "• Start container: ${YELLOW}docker start twscrape-postgres${NC}"
echo "• Remove container: ${YELLOW}docker rm twscrape-postgres${NC}"
echo ""
echo -e "${GREEN}Environment:${NC}"
echo "• Database URL: ${YELLOW}$TWSCRAPE_DATABASE_URL${NC}"
echo "• Virtual environment: ${YELLOW}.venv${NC}"
echo "• Environment file: ${YELLOW}.env${NC}"
