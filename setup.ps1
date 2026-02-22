param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$SkipDBCheck,
    [switch]$Force
)

Write-Host "CodeForge AI - Automated Setup (Windows)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

function Fail-OrContinue {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Red
    if (-not $Force) {
        Write-Host "Use -Force to continue past this error." -ForegroundColor Yellow
        exit 1
    } else {
        Write-Host "Continuing because -Force was specified." -ForegroundColor Yellow
    }
}

Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Python
try {
    $pythonVersion = python --version 2>$null
    if (-not $pythonVersion) { throw "Python not found" }
    Write-Host "OK  Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Fail-OrContinue "Python 3 is not installed. Install Python 3.11+ from https://python.org"
}

# Node.js
try {
    $nodeVersion = node --version 2>$null
    if (-not $nodeVersion) { throw "Node not found" }
    Write-Host "OK  Node.js found: $nodeVersion" -ForegroundColor Green
} catch {
    Fail-OrContinue "Node.js is not installed. Install Node.js 18+ from https://nodejs.org"
}

# PostgreSQL
if (-not $SkipDBCheck) {
    try {
        $pgVersion = psql --version 2>$null
        if (-not $pgVersion) { throw "psql not found" }
        Write-Host "OK  PostgreSQL found: $pgVersion" -ForegroundColor Green
    } catch {
        Write-Host "WARN PostgreSQL not found" -ForegroundColor Yellow
        if (-not $Force) {
            Write-Host "Install PostgreSQL 14+ from https://www.postgresql.org/download/windows/" -ForegroundColor Yellow
            $continue = Read-Host "Continue anyway? (y/n)"
            if ($continue -ne "y") { exit 1 }
        } else {
            Write-Host "Continuing without PostgreSQL because -Force was specified." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "SKIP PostgreSQL check (--SkipDBCheck)" -ForegroundColor Yellow
}

# Backend
if (-not $SkipBackend) {
    Write-Host ""
    Write-Host "Setting up Python backend..." -ForegroundColor Yellow

    if (-not (Test-Path "backend")) {
        Fail-OrContinue "'backend' directory not found."
    }

    Push-Location backend

    if (-not (Test-Path "venv")) {
        Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
        python -m venv venv
        if ($LASTEXITCODE -ne 0) {
            Fail-OrContinue "Failed to create virtual environment."
        }
    } else {
        Write-Host "OK  Virtual environment already exists" -ForegroundColor Green
    }

    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    .\venv\Scripts\Activate.ps1

    Write-Host "Upgrading pip..." -ForegroundColor Cyan
    python -m pip install --upgrade pip

    Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
    if (Test-Path "requirements.txt") {
        pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            Fail-OrContinue "Failed to install Python dependencies."
        }
    } else {
        Write-Host "WARN requirements.txt not found, skipping dependency install." -ForegroundColor Yellow
    }

    if (-not (Test-Path ".env")) {
        if (Test-Path ".env.example") {
            Write-Host "Creating .env from .env.example..." -ForegroundColor Cyan
            Copy-Item .env.example .env
            Write-Host "Edit backend.env with your API credentials." -ForegroundColor Yellow
        } else {
            Write-Host "WARN .env and .env.example not found. Create backend.env manually." -ForegroundColor Yellow
        }
    } else {
        Write-Host "OK  backend.env already exists" -ForegroundColor Green
    }

    Write-Host "OK  Backend setup complete" -ForegroundColor Green
    Pop-Location
} else {
    Write-Host "SKIP Backend setup (--SkipBackend)" -ForegroundColor Yellow
}

# Frontend
if (-not $SkipFrontend) {
    Write-Host ""
    Write-Host "Setting up React frontend..." -ForegroundColor Yellow

    if (-not (Test-Path "frontend")) {
        Fail-OrContinue "'frontend' directory not found."
    }

    Push-Location frontend

    Write-Host "Installing Node.js dependencies..." -ForegroundColor Cyan
    if (Test-Path "package.json") {
        npm install
        if ($LASTEXITCODE -ne 0) {
            Fail-OrContinue "Failed to install Node.js dependencies."
        }
    } else {
        Write-Host "WARN package.json not found, skipping npm install." -ForegroundColor Yellow
    }

    if (-not (Test-Path ".env.local")) {
        if (Test-Path ".env.local.example") {
            Write-Host "Creating .env.local from .env.local.example..." -ForegroundColor Cyan
            Copy-Item .env.local.example .env.local
        } else {
            Write-Host "WARN .env.local and .env.local.example not found. Create frontend.env.local manually." -ForegroundColor Yellow
        }
    } else {
        Write-Host "OK  frontend.env.local already exists" -ForegroundColor Green
    }

    Write-Host "OK  Frontend setup complete" -ForegroundColor Green
    Pop-Location
} else {
    Write-Host "SKIP Frontend setup (--SkipFrontend)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Configure API credentials in backend.env"
Write-Host "2. Start backend: cd backend; .\venv\Scripts\Activate.ps1; python main.py"
Write-Host "3. Start frontend: cd frontend; npm run dev"
Write-Host "4. Open http://localhost:3000"