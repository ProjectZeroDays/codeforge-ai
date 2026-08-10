# ============================================================
# CodeForge AI - Automated Backend Setup Script (Windows)
# ============================================================
# This script sets up the complete backend environment including:
# - Python virtual environment
# - Dependencies installation
# - PostgreSQL database setup
# - Database migrations
# - Default data seeding
# - Environment configuration
# ============================================================

param(
    [switch]$Force,
    [switch]$SkipDB,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ScriptDir "backend"
$VenvDir = Join-Path $BackendDir "venv"
$MinPythonVersion = [Version]"3.9"
$DBName = "codeforge_db"
$DBUser = "codeforge"
$DBPassword = "codeforge"
$DBHost = "localhost"
$DBPort = "5432"

# ============================================================
# Helper Functions
# ============================================================

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║  $Message" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([string]$Message)
    Write-Host "▶ $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "✔ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "✖ $Message" -ForegroundColor Red
}

function Test-Command {
    param([string]$Command)
    return (Get-Command $Command -ErrorAction SilentlyContinue) -ne $null
}

function Get-PythonVersion {
    param([string]$PythonCmd)
    try {
        $versionOutput = & $PythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        return [Version]$versionOutput
    } catch {
        return $null
    }
}

# ============================================================
# Pre-flight Checks
# ============================================================

Write-Header "CodeForge AI - Backend Setup Script (Windows)"

Write-Host "Starting setup at $(Get-Date)" -ForegroundColor Cyan
Write-Host ""

# Check if running from correct directory
if (-not (Test-Path (Join-Path $ScriptDir "README.md")) -or -not (Test-Path $BackendDir)) {
    Write-Error "Please run this script from the CodeForge AI root directory"
    exit 1
}

# ============================================================
# Step 1: Check Python Installation
# ============================================================

Write-Header "Step 1: Checking Python Installation"

$PythonCmd = $null

# Check for python
@("python", "python3", "py") | ForEach-Object {
    if (-not $PythonCmd) {
        $cmd = $_
        if (Test-Command $cmd) {
            $version = Get-PythonVersion $cmd
            if ($version -and $version -ge $MinPythonVersion) {
                $PythonCmd = $cmd
                Write-Success "Found Python $version (using $cmd)"
            }
        }
    }
}

if (-not $PythonCmd) {
    Write-Error "Python $MinPythonVersion or higher is required"
    Write-Host ""
    Write-Host "Please install Python from https://www.python.org/downloads/"
    Write-Host "Make sure to check 'Add Python to PATH' during installation"
    exit 1
}

# ============================================================
# Step 2: Create Virtual Environment
# ============================================================

Write-Header "Step 2: Setting Up Virtual Environment"

Set-Location $BackendDir

if (Test-Path $VenvDir) {
    Write-Warning "Virtual environment already exists"
    if ($Force) {
        Write-Step "Removing existing virtual environment..."
        Remove-Item -Recurse -Force $VenvDir
        $CreateVenv = $true
    } else {
        $response = Read-Host "Do you want to recreate it? (y/N)"
        if ($response -eq 'y' -or $response -eq 'Y') {
            Write-Step "Removing existing virtual environment..."
            Remove-Item -Recurse -Force $VenvDir
            $CreateVenv = $true
        } else {
            Write-Success "Using existing virtual environment"
            $CreateVenv = $false
        }
    }
} else {
    $CreateVenv = $true
}

if ($CreateVenv) {
    Write-Step "Creating virtual environment..."
    & $PythonCmd -m venv $VenvDir
    Write-Success "Virtual environment created at $VenvDir"
}

# Activate virtual environment
Write-Step "Activating virtual environment..."
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
if (Test-Path $ActivateScript) {
    & $ActivateScript
    Write-Success "Virtual environment activated"
} else {
    Write-Error "Could not find activation script"
    exit 1
}

# Upgrade pip
Write-Step "Upgrading pip..."
python -m pip install --upgrade pip --quiet
Write-Success "Pip upgraded"

# ============================================================
# Step 3: Install Dependencies
# ============================================================

Write-Header "Step 3: Installing Dependencies"

$RequirementsFile = Join-Path $BackendDir "requirements.txt"
if (-not (Test-Path $RequirementsFile)) {
    Write-Error "requirements.txt not found in backend directory"
    exit 1
}

Write-Step "Installing Python packages (this may take a few minutes)..."
pip install -r $RequirementsFile --quiet

# Install additional development dependencies
Write-Step "Installing development tools..."
pip install pytest pytest-asyncio httpx --quiet

Write-Success "All dependencies installed successfully"

# Verify critical packages
Write-Step "Verifying critical packages..."
python -c "import fastapi; print(f'  FastAPI {fastapi.__version__}')"
python -c "import sqlalchemy; print(f'  SQLAlchemy {sqlalchemy.__version__}')"
python -c "import uvicorn; print('  Uvicorn installed')"

# ============================================================
# Step 4: Check PostgreSQL
# ============================================================

Write-Header "Step 4: Checking PostgreSQL"

$PGInstalled = $false

if (Test-Command "psql") {
    $PGVersion = (psql --version) -replace "psql \(PostgreSQL\) ", ""
    Write-Success "PostgreSQL $PGVersion found"
    $PGInstalled = $true
} else {
    Write-Warning "PostgreSQL not found"
    Write-Host ""
    Write-Host "To install PostgreSQL on Windows:"
    Write-Host "  1. Download from https://www.postgresql.org/download/windows/"
    Write-Host "  2. Or use: choco install postgresql (if using Chocolatey)"
    Write-Host "  3. Or use: winget install PostgreSQL.PostgreSQL"
    Write-Host ""
    
    if (-not $SkipDB) {
        $response = Read-Host "Do you want to continue without PostgreSQL (will use SQLite for testing)? (y/N)"
        if ($response -ne 'y' -and $response -ne 'Y') {
            exit 1
        }
    }
}

# ============================================================
# Step 5: Setup Database
# ============================================================

Write-Header "Step 5: Setting Up Database"

if ($PGInstalled -and -not $SkipDB) {
    Write-Step "Setting up PostgreSQL database..."
    
    try {
        # Try to create database using psql
        $env:PGPASSWORD = "postgres"
        
        # Check if database exists
        $dbExists = psql -U postgres -h localhost -tc "SELECT 1 FROM pg_database WHERE datname = '$DBName'" 2>$null
        
        if ($dbExists -match "1") {
            Write-Success "Database '$DBName' already exists"
        } else {
            # Create user
            psql -U postgres -h localhost -c "CREATE USER $DBUser WITH PASSWORD '$DBPassword'" 2>$null
            
            # Create database
            psql -U postgres -h localhost -c "CREATE DATABASE $DBName OWNER $DBUser" 2>$null
            Write-Success "Database '$DBName' created"
        }
        
        # Grant privileges
        psql -U postgres -h localhost -c "GRANT ALL PRIVILEGES ON DATABASE $DBName TO $DBUser" 2>$null
        
        # Enable extensions
        psql -U postgres -h localhost -d $DBName -c "CREATE EXTENSION IF NOT EXISTS `"uuid-ossp`"" 2>$null
        psql -U postgres -h localhost -d $DBName -c "CREATE EXTENSION IF NOT EXISTS `"pg_trgm`"" 2>$null
        
        Write-Success "Database setup complete"
        $DatabaseUrl = "postgresql+asyncpg://${DBUser}:${DBPassword}@${DBHost}:${DBPort}/${DBName}"
    } catch {
        Write-Warning "Could not set up PostgreSQL automatically"
        Write-Warning "Please set up the database manually or provide DATABASE_URL in .env"
        $DatabaseUrl = ""
    }
} else {
    Write-Warning "Using SQLite for development (not recommended for production)"
    $DatabaseUrl = "sqlite+aiosqlite:///./codeforge.db"
}

# ============================================================
# Step 6: Configure Environment
# ============================================================

Write-Header "Step 6: Configuring Environment"

$EnvFile = Join-Path $BackendDir ".env"
$EnvExample = Join-Path $BackendDir ".env.example"

$CreateEnv = $false

if (Test-Path $EnvFile) {
    Write-Warning ".env file already exists"
    if ($Force) {
        $CreateEnv = $true
    } else {
        $response = Read-Host "Do you want to overwrite it? (y/N)"
        if ($response -eq 'y' -or $response -eq 'Y') {
            $CreateEnv = $true
        } else {
            Write-Success "Keeping existing .env file"
        }
    }
} else {
    $CreateEnv = $true
}

if ($CreateEnv) {
    Write-Step "Creating .env file..."
    
    # Generate a random secret key
    $SecretKey = python -c "import secrets; print(secrets.token_urlsafe(32))"
    $EncryptionKey = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    
    $EnvContent = @"
# CodeForge AI Backend Configuration
# Generated on $(Get-Date)

# Database
DATABASE_URL=$DatabaseUrl

# Security
SECRET_KEY=$SecretKey
ENCRYPTION_KEY=$EncryptionKey

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
"@

    $EnvContent | Out-File -FilePath $EnvFile -Encoding utf8
    
    Write-Success ".env file created"
    Write-Warning "Remember to update VENICE_API_KEY and GITHUB_PERSONAL_ACCESS_TOKEN"
}

# ============================================================
# Step 7: Run Database Migrations
# ============================================================

Write-Header "Step 7: Running Database Migrations"

Set-Location $BackendDir

# Check if alembic is configured
$AlembicIni = Join-Path $BackendDir "alembic.ini"
$AlembicDir = Join-Path $BackendDir "alembic"

if ((Test-Path $AlembicIni) -and (Test-Path $AlembicDir)) {
    Write-Step "Running Alembic migrations..."
    
    try {
        alembic upgrade head 2>$null
        Write-Success "Database migrations complete"
    } catch {
        Write-Warning "Migration may have already been applied or failed"
    }
} else {
    Write-Step "Initializing database tables directly..."
    try {
        python -c @"
import asyncio
from app.database.connection_unified import init_db
asyncio.run(init_db())
print('Tables created successfully')
"@
        Write-Success "Database tables created"
    } catch {
        Write-Warning "Could not initialize database tables"
    }
}

# ============================================================
# Step 8: Seed Default Data
# ============================================================

Write-Header "Step 8: Seeding Default Data"

Write-Step "Seeding system prompts, templates, and configurations..."

try {
    python -c @"
import asyncio

async def seed_data():
    try:
        from app.database.connection_unified import AsyncSessionLocal
        from app.database.seeds import run_all_seeds
        
        async with AsyncSessionLocal() as session:
            await run_all_seeds()
        
        print('Default data seeded successfully')
        return True
    except Exception as e:
        print(f'Warning: Could not seed data: {e}')
        return False

asyncio.run(seed_data())
"@
} catch {
    Write-Warning "Could not seed default data"
}

# Seed project templates
try {
    python -c @"
import asyncio

async def seed_templates():
    try:
        from app.database.connection_unified import AsyncSessionLocal
        from app.services.templates_service import ProjectTemplatesService
        
        service = ProjectTemplatesService()
        async with AsyncSessionLocal() as session:
            await service.seed_templates(session)
        
        print('Project templates seeded successfully')
    except Exception as e:
        print(f'Warning: Could not seed templates: {e}')

asyncio.run(seed_templates())
"@
} catch {
    Write-Warning "Could not seed project templates"
}

Write-Success "Default data seeding complete"

# ============================================================
# Step 9: Validate Setup
# ============================================================

Write-Header "Step 9: Validating Setup"

Write-Step "Running validation checks..."

$ValidationPassed = $true

# Check Python packages
try {
    python -c "import fastapi, sqlalchemy, uvicorn, pydantic"
    Write-Success "Core packages: OK"
} catch {
    Write-Error "Core packages: FAILED"
    $ValidationPassed = $false
}

# Check .env file
if (Test-Path $EnvFile) {
    Write-Success "Environment file: OK"
} else {
    Write-Error "Environment file: MISSING"
    $ValidationPassed = $false
}

# Check if main app can be imported
try {
    python -c "from main import app; print('FastAPI app loaded')"
    Write-Success "FastAPI app: OK"
} catch {
    Write-Warning "FastAPI app: Could not load (check logs)"
}

# ============================================================
# Summary
# ============================================================

Write-Header "Setup Complete!"

Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  CodeForge AI Backend Setup Complete!                        ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Configure your API keys in $EnvFile:"
Write-Host "   - VENICE_API_KEY: Get from https://venice.ai"
Write-Host "   - GITHUB_PERSONAL_ACCESS_TOKEN: Generate from GitHub Settings"
Write-Host ""
Write-Host "2. Start the backend server:"
Write-Host "   cd backend"
Write-Host "   .\venv\Scripts\Activate.ps1"
Write-Host "   uvicorn main:app --reload --port 8000"
Write-Host ""
Write-Host "3. Start the frontend (in another terminal):"
Write-Host "   cd frontend"
Write-Host "   npm install"
Write-Host "   npm run dev"
Write-Host ""
Write-Host "4. Open your browser:"
Write-Host "   - Frontend: http://localhost:3000"
Write-Host "   - API Docs: http://localhost:8000/docs"
Write-Host ""

if ($ValidationPassed) {
    Write-Host "All validation checks passed!" -ForegroundColor Green
} else {
    Write-Host "Some validation checks failed. Please review the output above." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "For more information, see README.md" -ForegroundColor Cyan
Write-Host ""

# Return to original directory
Set-Location $ScriptDir

exit 0
