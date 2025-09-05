# Railway Auto-deploys with NIXPACKS, but this Dockerfile can be used for local/debugging
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway will set the PORT environment variable
EXPOSE 8000

# Start the application
CMD ["python", "wsgi.py"]