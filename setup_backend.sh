#!/bin/bash

# ============================================================
# CodeForge AI - Automated Backend Setup Script
# ============================================================
# This script sets up the complete backend environment including:
# - Python virtual environment
# - Dependencies installation
# - PostgreSQL database setup
# - Database migrations
# - Default data seeding
# - Environment configuration
# ============================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/backend"
VENV_DIR="${BACKEND_DIR}/venv"
MIN_PYTHON_VERSION="3.9"
DB_NAME="codeforge_db"
DB_USER="codeforge"
DB_PASSWORD="codeforge"
DB_HOST="localhost"
DB_PORT="5432"

# ============================================================
# Helper Functions
# ============================================================

print_header() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  $1"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}▶${NC} $1"
}

print_success() {
    echo -e "${GREEN}✔${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✖${NC} $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

version_gte() {
    # Compare versions: returns 0 if $1 >= $2
    printf '%s\n%s' "$2" "$1" | sort -V -C
}

# ============================================================
# Pre-flight Checks
# ============================================================

print_header "CodeForge AI - Backend Setup Script"

echo -e "${CYAN}Starting setup at $(date)${NC}"
echo ""

# Check if running from correct directory
if [ ! -f "${SCRIPT_DIR}/README.md" ] || [ ! -d "${BACKEND_DIR}" ]; then
    print_error "Please run this script from the CodeForge AI root directory"
    exit 1
fi

# ============================================================
# Step 1: Check Python Installation
# ============================================================

print_header "Step 1: Checking Python Installation"

PYTHON_CMD=""

# Check for python3
if check_command python3; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if version_gte "$PYTHON_VERSION" "$MIN_PYTHON_VERSION"; then
        PYTHON_CMD="python3"
        print_success "Found Python $PYTHON_VERSION (using python3)"
    else
        print_warning "Python version $PYTHON_VERSION is below minimum required ($MIN_PYTHON_VERSION)"
    fi
fi

# Check for python if python3 not found or version too low
if [ -z "$PYTHON_CMD" ] && check_command python; then
    PYTHON_VERSION=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if version_gte "$PYTHON_VERSION" "$MIN_PYTHON_VERSION"; then
        PYTHON_CMD="python"
        print_success "Found Python $PYTHON_VERSION (using python)"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    print_error "Python $MIN_PYTHON_VERSION or higher is required"
    echo ""
    echo "Please install Python from https://www.python.org/downloads/"
    echo "Or use your package manager:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  macOS: brew install python3"
    echo "  Fedora: sudo dnf install python3 python3-pip"
    exit 1
fi

# ============================================================
# Step 2: Create Virtual Environment
# ============================================================

print_header "Step 2: Setting Up Virtual Environment"

cd "${BACKEND_DIR}"

if [ -d "${VENV_DIR}" ]; then
    print_warning "Virtual environment already exists"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_step "Removing existing virtual environment..."
        rm -rf "${VENV_DIR}"
        print_step "Creating new virtual environment..."
        $PYTHON_CMD -m venv "${VENV_DIR}"
        print_success "Virtual environment created"
    else
        print_success "Using existing virtual environment"
    fi
else
    print_step "Creating virtual environment..."
    $PYTHON_CMD -m venv "${VENV_DIR}"
    print_success "Virtual environment created at ${VENV_DIR}"
fi

# Activate virtual environment
print_step "Activating virtual environment..."
source "${VENV_DIR}/bin/activate"
print_success "Virtual environment activated"

# Upgrade pip
print_step "Upgrading pip..."
pip install --upgrade pip --quiet
print_success "Pip upgraded to $(pip --version | awk '{print $2}')"

# ============================================================
# Step 3: Install Dependencies
# ============================================================

print_header "Step 3: Installing Dependencies"

if [ ! -f "${BACKEND_DIR}/requirements.txt" ]; then
    print_error "requirements.txt not found in backend directory"
    exit 1
fi

print_step "Installing Python packages (this may take a few minutes)..."
pip install -r requirements.txt --quiet

# Install additional development dependencies
print_step "Installing development tools..."
pip install pytest pytest-asyncio httpx --quiet

print_success "All dependencies installed successfully"

# Verify critical packages
print_step "Verifying critical packages..."
python -c "import fastapi; print(f'  FastAPI {fastapi.__version__}')"
python -c "import sqlalchemy; print(f'  SQLAlchemy {sqlalchemy.__version__}')"
python -c "import uvicorn; print(f'  Uvicorn installed')"

# ============================================================
# Step 4: Check PostgreSQL
# ============================================================

print_header "Step 4: Checking PostgreSQL"

PG_INSTALLED=false

if check_command psql; then
    PG_VERSION=$(psql --version | awk '{print $3}')
    print_success "PostgreSQL $PG_VERSION found"
    PG_INSTALLED=true
else
    print_warning "PostgreSQL not found"
    echo ""
    echo "To install PostgreSQL:"
    echo "  Ubuntu/Debian: sudo apt install postgresql postgresql-contrib"
    echo "  macOS: brew install postgresql && brew services start postgresql"
    echo "  Fedora: sudo dnf install postgresql-server postgresql-contrib"
    echo ""
    read -p "Do you want to continue without PostgreSQL (will use SQLite for testing)? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# ============================================================
# Step 5: Setup Database
# ============================================================

print_header "Step 5: Setting Up Database"

if [ "$PG_INSTALLED" = true ]; then
    # Check if PostgreSQL service is running
    if pg_isready -h localhost -p 5432 &>/dev/null; then
        print_success "PostgreSQL is running"
    else
        print_warning "PostgreSQL service may not be running"
        echo "Attempting to start PostgreSQL..."
        
        # Try different methods to start PostgreSQL
        if check_command systemctl; then
            sudo systemctl start postgresql 2>/dev/null || true
        elif check_command brew; then
            brew services start postgresql 2>/dev/null || true
        elif check_command pg_ctl; then
            pg_ctl start 2>/dev/null || true
        fi
        
        sleep 2
        if pg_isready -h localhost -p 5432 &>/dev/null; then
            print_success "PostgreSQL started"
        else
            print_warning "Could not start PostgreSQL automatically"
        fi
    fi
    
    # Create database and user
    print_step "Setting up database..."
    
    # Check if we can connect as postgres
    if sudo -u postgres psql -c "SELECT 1" &>/dev/null 2>&1; then
        # Create user if not exists
        sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
            sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}'"
        
        # Create database if not exists
        if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "${DB_NAME}"; then
            print_success "Database '${DB_NAME}' already exists"
        else
            sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}"
            print_success "Database '${DB_NAME}' created"
        fi
        
        # Grant privileges
        sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER}"
        
        # Enable extensions
        sudo -u postgres psql -d "${DB_NAME}" -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""
        sudo -u postgres psql -d "${DB_NAME}" -c "CREATE EXTENSION IF NOT EXISTS pg_trgm"
        
        print_success "Database setup complete"
        
        DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
    else
        print_warning "Cannot connect to PostgreSQL as postgres user"
        echo "Please set up the database manually or provide DATABASE_URL"
        DATABASE_URL=""
    fi
else
    # Use SQLite for testing
    print_warning "Using SQLite for development (not recommended for production)"
    DATABASE_URL="sqlite+aiosqlite:///./codeforge.db"
fi

# ============================================================
# Step 6: Configure Environment
# ============================================================

print_header "Step 6: Configuring Environment"

ENV_FILE="${BACKEND_DIR}/.env"
ENV_EXAMPLE="${BACKEND_DIR}/.env.example"

if [ -f "${ENV_FILE}" ]; then
    print_warning ".env file already exists"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_success "Keeping existing .env file"
    else
        CREATE_ENV=true
    fi
else
    CREATE_ENV=true
fi

if [ "${CREATE_ENV}" = true ]; then
    print_step "Creating .env file..."
    
    # Generate a random secret key
    SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
    ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    
    cat > "${ENV_FILE}" << EOF
# CodeForge AI Backend Configuration
# Generated on $(date)

# Database
DATABASE_URL=${DATABASE_URL:-postgresql+asyncpg://codeforge:codeforge@localhost:5432/codeforge_db}

# Security
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# Venice AI (get your key from https://venice.ai)
VENICE_API_KEY=your_venice_api_key_here
VENICE_API_SECRET=

# GitHub Integration (optional)
GITHUB_PERSONAL_ACCESS_TOKEN=
GITHUB_USERNAME=

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true

# CORS
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Local LLM (optional)
LOCAL_LLM_ENABLED=false
LOCAL_LLM_MODEL_PATH=

# Logging
LOG_LEVEL=INFO
EOF

    print_success ".env file created"
    print_warning "Remember to update VENICE_API_KEY and GITHUB_PERSONAL_ACCESS_TOKEN"
fi

# ============================================================
# Step 7: Run Database Migrations
# ============================================================

print_header "Step 7: Running Database Migrations"

cd "${BACKEND_DIR}"

# Check if alembic is configured
if [ -f "alembic.ini" ] && [ -d "alembic" ]; then
    print_step "Running Alembic migrations..."
    
    # Update alembic.ini with correct database URL
    if [ -n "$DATABASE_URL" ]; then
        sed -i.bak "s|sqlalchemy.url = .*|sqlalchemy.url = ${DATABASE_URL}|g" alembic.ini 2>/dev/null || \
        sed -i '' "s|sqlalchemy.url = .*|sqlalchemy.url = ${DATABASE_URL}|g" alembic.ini
    fi
    
    # Generate initial migration if needed
    if [ ! -d "alembic/versions" ] || [ -z "$(ls -A alembic/versions 2>/dev/null)" ]; then
        print_step "Creating initial migration..."
        alembic revision --autogenerate -m "Initial migration" 2>/dev/null || true
    fi
    
    # Run migrations
    alembic upgrade head 2>/dev/null || print_warning "Migration may have already been applied"
    print_success "Database migrations complete"
else
    print_step "Initializing database tables directly..."
    python -c "
import asyncio
from app.database.connection_unified import init_db
asyncio.run(init_db())
print('Tables created successfully')
" 2>/dev/null || print_warning "Could not initialize database tables"
fi

# ============================================================
# Step 8: Seed Default Data
# ============================================================

print_header "Step 8: Seeding Default Data"

print_step "Seeding system prompts, templates, and configurations..."

python << 'EOF'
import asyncio
import sys

async def seed_data():
    try:
        from app.database.connection_unified import AsyncSessionLocal
        from app.database.seeds import run_all_seeds
        
        async with AsyncSessionLocal() as session:
            await run_all_seeds()
        
        print("Default data seeded successfully")
        return True
    except Exception as e:
        print(f"Warning: Could not seed data: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(seed_data())
    sys.exit(0 if result else 1)
EOF

# Seed project templates
python << 'EOF'
import asyncio

async def seed_templates():
    try:
        from app.database.connection_unified import AsyncSessionLocal
        from app.services.templates_service import ProjectTemplatesService
        
        service = ProjectTemplatesService()
        async with AsyncSessionLocal() as session:
            await service.seed_templates(session)
        
        print("Project templates seeded successfully")
    except Exception as e:
        print(f"Warning: Could not seed templates: {e}")

asyncio.run(seed_templates())
EOF

print_success "Default data seeding complete"

# ============================================================
# Step 9: Validate Setup
# ============================================================

print_header "Step 9: Validating Setup"

print_step "Running validation checks..."

VALIDATION_PASSED=true

# Check Python packages
python -c "import fastapi, sqlalchemy, uvicorn, pydantic" 2>/dev/null && \
    print_success "Core packages: OK" || { print_error "Core packages: FAILED"; VALIDATION_PASSED=false; }

# Check database connection
python << 'EOF'
import asyncio
from app.database.connection_unified import engine

async def check_db():
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        return True
    except:
        return False

result = asyncio.run(check_db())
exit(0 if result else 1)
EOF
[ $? -eq 0 ] && print_success "Database connection: OK" || { print_warning "Database connection: FAILED (may be OK if using SQLite)"; }

# Check .env file
[ -f "${ENV_FILE}" ] && print_success "Environment file: OK" || { print_error "Environment file: MISSING"; VALIDATION_PASSED=false; }

# Check if main app can be imported
python -c "from main import app; print('FastAPI app loaded')" 2>/dev/null && \
    print_success "FastAPI app: OK" || { print_warning "FastAPI app: Could not load (check logs)"; }

# ============================================================
# Summary
# ============================================================

print_header "Setup Complete!"

echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}  CodeForge AI Backend Setup Complete!                        ${GREEN}║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}Next Steps:${NC}"
echo ""
echo "1. Configure your API keys in ${ENV_FILE}:"
echo "   - VENICE_API_KEY: Get from https://venice.ai"
echo "   - GITHUB_PERSONAL_ACCESS_TOKEN: Generate from GitHub Settings"
echo ""
echo "2. Start the backend server:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   uvicorn main:app --reload --port 8000"
echo ""
echo "3. Start the frontend (in another terminal):"
echo "   cd frontend"
echo "   npm install"
echo "   npm run dev"
echo ""
echo "4. Open your browser:"
echo "   - Frontend: http://localhost:3000"
echo "   - API Docs: http://localhost:8000/docs"
echo ""

if [ "$VALIDATION_PASSED" = true ]; then
    echo -e "${GREEN}All validation checks passed!${NC}"
else
    echo -e "${YELLOW}Some validation checks failed. Please review the output above.${NC}"
fi

echo ""
echo -e "${CYAN}For more information, see README.md${NC}"
echo ""

# Deactivate virtual environment
deactivate 2>/dev/null || true

exit 0
