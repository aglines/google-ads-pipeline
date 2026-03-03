FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY README.md .

# Copy source code
COPY dbt/ dbt/
COPY scripts/ scripts/
COPY airflow/ airflow/
COPY tests/ tests/
COPY config/ config/

# Install dependencies
RUN uv sync

# Set environment variables
ENV AIRFLOW_HOME=/app/airflow
ENV PYTHONUNBUFFERED=1

# Expose Airflow webserver port
EXPOSE 8080

# Default command
CMD ["uv", "run", "airflow", "standalone"]
