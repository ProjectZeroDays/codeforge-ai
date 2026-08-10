#!/bin/bash
# Build script for macOS
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_DIR="$ROOT_DIR/backend"
ELECTRON_DIR="$ROOT_DIR/electron"
APP_DIR="$ELECTRON_DIR/app"

echo "========================================"
echo "CodeForge AI - macOS Build"
echo "========================================"

# Step 1: Build frontend
echo ""
echo "=== Step 1: Building Next.js frontend ==="
cd "$FRONTEND_DIR"
npm run build

# Step 2: Prepare backend
echo ""
echo "=== Step 2: Preparing backend ==="
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/backend"
mkdir -p "$APP_DIR/frontend"

cp -R "$BACKEND_DIR"/* "$APP_DIR/backend/"
cp -R "$FRONTEND_DIR/out"/* "$APP_DIR/frontend/"

# Remove cache files
find "$APP_DIR/backend" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$APP_DIR/backend" -type d -name "venv" -exec rm -rf {} + 2>/dev/null || true
find "$APP_DIR/backend" -type d -name ".venv" -exec rm -rf {} + 2>/dev/null || true

# Remove database files
rm -f "$APP_DIR/backend/codeforge.db"
rm -f "$APP_DIR/backend/codeforge.db-wal"
rm -f "$APP_DIR/backend/codeforge.db-shm"

echo "Backend prepared"

# Step 3: Package for macOS
echo ""
echo "=== Step 3: Packaging for macOS ==="
cd "$ELECTRON_DIR"
npx electron-builder --mac --x64

echo ""
echo "========================================"
echo "Build complete!"
echo "Output: $ELECTRON_DIR/dist"
echo "========================================"
