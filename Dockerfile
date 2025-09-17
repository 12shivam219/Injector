# Dockerfile for high-performance deployment of Resume Customizer Pro
# Optimized for Streamlit with proper dependencies and security

FROM python:3.11-slim

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user for security
RUN groupadd -r streamlit && useradd -r -g streamlit streamlit

# Set workdir
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt ./
COPY requirements-gdrive.txt ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -r requirements-gdrive.txt

# Copy application code
COPY --chown=streamlit:streamlit . .

# Create necessary directories
RUN mkdir -p logs uploads temp && \
    chown -R streamlit:streamlit /app

# Switch to non-root user
USER streamlit

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health

# Expose port
EXPOSE 8501

# Start Redis in background and run Streamlit
CMD redis-server --daemonize yes && \
    streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=true \
    --server.maxUploadSize=200
