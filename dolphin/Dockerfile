FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for PyTorch and image processing
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy inference server code
COPY inference_server.py /app/

# Create directories for models and uploads
RUN mkdir -p /app/models /app/uploads

# Expose FastAPI port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Start FastAPI server
CMD ["uvicorn", "inference_server:app", "--host", "0.0.0.0", "--port", "8001"]
