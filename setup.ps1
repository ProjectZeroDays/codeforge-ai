# CodeForge AI - Automated Setup Script for Windows
# Run with: .\setup.ps1

Write-Host "🚀 CodeForge AI - Automated Setup" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "🔍 Checking prerequisites..." -ForegroundColor Yellow

# Check Python
try {
    $pythonVersion = python --version
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python 3 is not installed" -ForegroundColor Red
    Write-Host "Please install Python 3.11+ from https://python.org" -ForegroundColor Red
    exit 1
}

# Check Node.js
try {
    $nodeVersion = node --version
    Write-Host "✓ Node.js found: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js is not installed" -ForegroundColor Red
    Write-Host "Please install Node.js 18+ from https://nodejs.org" -ForegroundColor Red
    exit 1
}

# Check PostgreSQL
$pgFound = $false
try {
    $pgVersion = psql --version
    Write-Host "✓ PostgreSQL found: $pgVersion" -ForegroundColor Green
    $pgFound = $true
} catch {
    Write-Host "⚠  PostgreSQL not found" -ForegroundColor Yellow
    Write-Host "Please install PostgreSQL 14+ from https://www.postgresql.org/download/windows/" -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit 1
    }
}

# Initialize database (matches setup.sh behavior)
if ($pgFound) {
    $initSql = Join-Path $PSScriptRoot "database\init.sql"
    if (Test-Path $initSql) {
        Write-Host "📊 Running database initialization..." -ForegroundColor Yellow
        try {
            psql -U postgres -f $initSql 2>$null
            Write-Host "✓ Database initialized" -ForegroundColor Green
        } catch {
            Write-Host "⚠  Database init may have already been applied or failed" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "🐍 Setting up Python backend..." -ForegroundColor Yellow

Set-Location backend

# Create virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
    python -m venv venv
}

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

# Create .env if doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file..." -ForegroundColor Cyan
    Copy-Item .env.example .env
    Write-Host "⚠  Please edit backend\.env with your API credentials" -ForegroundColor Yellow
}

Write-Host "✓ Backend setup complete" -ForegroundColor Green

Set-Location ..

Write-Host ""
Write-Host "⚛️  Setting up React frontend..." -ForegroundColor Yellow

Set-Location frontend

# Install dependencies
Write-Host "Installing Node.js dependencies..." -ForegroundColor Cyan
npm install

# Create .env.local if doesn't exist
if (-not (Test-Path ".env.local")) {
    Write-Host "Creating .env.local file..." -ForegroundColor Cyan
    Copy-Item .env.local.example .env.local
}

Write-Host "✓ Frontend setup complete" -ForegroundColor Green

Set-Location ..

Write-Host ""
Write-Host "✓✓✓ Setup complete! ✓✓✓" -ForegroundColor Green
Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "📝 Next Steps:" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Configure API credentials:"
Write-Host "   notepad backend\.env" -ForegroundColor Yellow
Write-Host ""
Write-Host "   Required:"
Write-Host "   - VENICE_API_KEY"
Write-Host "   - VENICE_API_SECRET"
Write-Host "   - GITHUB_PERSONAL_ACCESS_TOKEN"
Write-Host "   - GITHUB_USERNAME"
Write-Host ""
Write-Host "2. Start the backend server:"
Write-Host "   cd backend" -ForegroundColor Green
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host "   python main.py" -ForegroundColor Green
Write-Host ""
Write-Host "3. In a new terminal, start the frontend:"
Write-Host "   cd frontend" -ForegroundColor Green
Write-Host "   npm run dev" -ForegroundColor Green
Write-Host ""
Write-Host "4. Open your browser:"
Write-Host "   http://localhost:3000" -ForegroundColor Green
Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "🚀 Happy coding with CodeForge AI!" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan