#!/bin/bash

# CodeForge AI - Automated Setup Script
# This script sets up the complete development environment

set -e  # Exit on any error

echo "🚀 CodeForge AI - Automated Setup"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}Please do not run this script as root${NC}"
   exit 1
fi

echo "🔍 Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js found${NC}"

# Check PostgreSQL
if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}⚠  PostgreSQL not found. Installing...${NC}"
    sudo apt-get update
    sudo apt-get install -y postgresql postgresql-contrib
fi
echo -e "${GREEN}✓ PostgreSQL found${NC}"

echo ""
echo "📦 Setting up database..."

# Start PostgreSQL if not running
sudo systemctl start postgresql

# Create database and user
echo "Creating database and user..."
sudo -u postgres psql -f database/init.sql || echo "Database may already exist"

echo -e "${GREEN}✓ Database setup complete${NC}"

echo ""
echo "🐍 Setting up Python backend..."

cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create .env if doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo -e "${YELLOW}⚠  Please edit backend/.env with your API credentials${NC}"
fi

echo -e "${GREEN}✓ Backend setup complete${NC}"

cd ..

echo ""
echo "⚛️  Setting up React frontend..."

cd frontend

# Install dependencies
echo "Installing Node.js dependencies..."
npm install

# Create .env.local if doesn't exist
if [ ! -f ".env.local" ]; then
    echo "Creating .env.local file..."
    cp .env.local.example .env.local
fi

echo -e "${GREEN}✓ Frontend setup complete${NC}"

cd ..

echo ""
echo -e "${GREEN}✓✓✓ Setup complete! ✓✓✓${NC}"
echo ""
echo "=================================="
echo "📝 Next Steps:"
echo "=================================="
echo ""
echo "1. Configure API credentials:"
echo "   ${YELLOW}nano backend/.env${NC}"
echo ""
echo "   Required:"
echo "   - VENICE_API_KEY"
echo "   - VENICE_API_SECRET"
echo "   - GITHUB_PERSONAL_ACCESS_TOKEN"
echo "   - GITHUB_USERNAME"
echo ""
echo "2. Start the backend server:"
echo "   ${GREEN}cd backend${NC}"
echo "   ${GREEN}source venv/bin/activate${NC}"
echo "   ${GREEN}python main.py${NC}"
echo ""
echo "3. In a new terminal, start the frontend:"
echo "   ${GREEN}cd frontend${NC}"
echo "   ${GREEN}npm run dev${NC}"
echo ""
echo "4. Open your browser:"
echo "   ${GREEN}http://localhost:3000${NC}"
echo ""
echo "=================================="
echo "🚀 Happy coding with CodeForge AI!"
echo "=================================="