FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY ml/training/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy training code
COPY ml/training/ ./training/
COPY ml/models/ ./models/

# Set environment variables
ENV PYTHONPATH=/app
ENV MLFLOW_TRACKING_URI=http://mlflow:5000

# Run training
CMD ["python", "training/train.py"]