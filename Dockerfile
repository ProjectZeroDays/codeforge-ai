# =============================================================================
# CodeForge AI - HuggingFace Spaces Optimized Dockerfile
# =============================================================================
# Multi-stage build for minimal image size
# Optimized for HF Spaces free tier (CPU-only, 16GB max memory)
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Frontend Builder
# -----------------------------------------------------------------------------
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files first for better caching
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --only=production=false

# Copy frontend source
COPY frontend/ ./

# Build Next.js production bundle
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

# Set API URLs for production build
ENV NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_WS_URL=ws://localhost:7860

RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: Python Dependencies Builder
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS python-builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY backend/requirements.txt ./
COPY hf_requirements.txt ./

# Install dependencies (using HF-specific requirements if available)
RUN pip install --no-cache-dir --upgrade pip && \
    if [ -f hf_requirements.txt ]; then \
        pip install --no-cache-dir -r hf_requirements.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# -----------------------------------------------------------------------------
# Stage 3: Final Production Image
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    NODE_ENV=production \
    PORT=7860 \
    HOST=0.0.0.0

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    nodejs \
    npm \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy Python virtual environment from builder
COPY --from=python-builder /opt/venv /opt/venv

# Copy backend code
COPY backend/ ./backend/

# Copy frontend build and dependencies
COPY --from=frontend-builder /app/frontend/.next ./frontend/.next
COPY --from=frontend-builder /app/frontend/node_modules ./frontend/node_modules
COPY --from=frontend-builder /app/frontend/package.json ./frontend/
COPY --from=frontend-builder /app/frontend/public ./frontend/public
COPY --from=frontend-builder /app/frontend/next.config.js ./frontend/

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Create data directory for SQLite
RUN mkdir -p /app/data && chmod 777 /app/data

# Create non-root user for HF Spaces
RUN useradd -m -u 1000 user
RUN chown -R user:user /app
USER user

# Expose HF Spaces standard port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Start services
CMD ["/app/start.sh"]
