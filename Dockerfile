# Dockerfile for Hugging Face Spaces (Flask + FAISS + Gemini)
FROM python:3.11-slim

# metadata
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal system deps required for faiss and PDFs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libgomp1 \
    libopenblas-dev \
    libblas-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker cache
COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r /app/requirements.txt

# Copy the rest of the repo
COPY . /app

# Ensure FAISS_DIR default exists and is writable
RUN mkdir -p /app/qa_faiss_store && chmod -R a+rwx /app/qa_faiss_store

# Expose port 7860 (Spaces commonly uses this port)
EXPOSE 7860

# Use gunicorn to run the app; bind to 0.0.0.0:7860
# Ensure your Flask app exposes a module app:app (app/__init__.py sets app = create_app())
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app", "--workers", "2", "--threads", "4", "--timeout", "120"]
