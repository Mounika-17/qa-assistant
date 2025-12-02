FROM python:3.10-slim-buster

WORKDIR /app

# Install FAISS dependencies (important!)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 libopenblas-dev libblas-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Production server
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app", "--workers", "2", "--threads", "4"]
