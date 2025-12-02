# Use 'bullseye' (Debian 11) instead of 'buster' (Debian 10, EOL).
# This resolves the 404/Release file errors during apt-get update.
FROM python:3.10-slim-bullseye

WORKDIR /app

# Install FAISS dependencies (important!)
# Note: This step should now work as the 'bullseye' repositories are active.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 libopenblas-dev libblas-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . /app

# Standard environment variable for unbuffered Python output
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Production server command using gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app", "--workers", "2", "--threads", "4"]