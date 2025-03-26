FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11-slim
ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=100
WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    postgresql-client \
    python3-dev \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

# Copy poetry.lock* in case it doesn't exist in the repo
COPY app/pyproject.toml app/poetry.lock* /code/

# Allow installing dev dependencies to run tests
ARG INSTALL_DEV=false
RUN bash -c "if [ $INSTALL_DEV == 'true' ] ; then poetry install --no-root ; else poetry install --no-root --only main ; fi"

# Install additional packages needed for Celery and PostgreSQL
RUN pip install --no-cache-dir psycopg2-binary celery[redis] watchfiles

# Create health check endpoint
RUN mkdir -p /code/app
RUN echo 'from fastapi import FastAPI, status; app = FastAPI(); @app.get("/health", status_code=status.HTTP_200_OK); def health(): return {"status": "healthy"}' > /code/app/health.py

ENV PYTHONPATH=/code
EXPOSE 8000
