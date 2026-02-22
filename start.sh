#!/bin/bash
# =============================================================================
# CodeForge AI - Startup Script for HuggingFace Spaces
# =============================================================================

set -e

echo "=================================================="
echo "Starting CodeForge AI on HuggingFace Spaces"
echo "=================================================="

# Set default environment variables
export DATABASE_URL=${DATABASE_URL:-"sqlite:///app/data/codeforge.db"}
export USE_SQLITE=${USE_SQLITE:-"true"}
export SECRET_KEY=${SECRET_KEY:-"hf-spaces-default-key-change-me"}
export HOST=${HOST:-"0.0.0.0"}
export PORT=${PORT:-"7860"}

# Create data directory if it doesn't exist
mkdir -p /app/data

echo "Database URL: $DATABASE_URL"
echo "Using SQLite: $USE_SQLITE"

# Initialize database
echo "Initializing database..."
cd /app/backend
python -c "
import asyncio
import sys
sys.path.insert(0, '/app')
from backend.app.database.connection import init_db
asyncio.run(init_db())
print('Database initialized successfully')
" || echo "Database initialization skipped or failed"

# Run seeds
echo "Running database seeds..."
python -c "
import asyncio
import sys
sys.path.insert(0, '/app')
from backend.app.database.seeds import run_all_seeds
asyncio.run(run_all_seeds())
print('Seeds completed successfully')
" || echo "Seeds skipped or failed"

echo "Starting services with Supervisor..."
cd /app
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
