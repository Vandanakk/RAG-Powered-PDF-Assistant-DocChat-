# Multi-stage Dockerfile for DocChat (RAG-Powered PDF Assistant)

# -------------------------------------------------------------
# Stage 1: Build Frontend (Vite + React + TypeScript + Tailwind)
# -------------------------------------------------------------
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
# Build with default relative API path (/api) for unified serving
ENV VITE_API_BASE_URL=/api
RUN npm run build

# -------------------------------------------------------------
# Stage 2: Production Python Backend Runtime
# -------------------------------------------------------------
FROM python:3.11-slim AS runner
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application source code
COPY backend/app ./app

# Copy built frontend assets into frontend_dist
COPY --from=frontend-builder /app/frontend/dist ./frontend_dist

# Create data directory for ChromaDB vector store & registry
RUN mkdir -p /app/data/chroma

# Environment configuration
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/data

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# Start uvicorn server with dynamic port support ($PORT)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
