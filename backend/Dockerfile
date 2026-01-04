FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=100
WORKDIR /code
# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install system dependencies
RUN apt clean && apt update && apt install curl libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info -y

# Install dependencies
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy project definition
COPY app/pyproject.toml app/uv.lock /code/

# Configure the virtual environment path
ENV UV_PROJECT_ENVIRONMENT="/venv"

# Place the application in the virtual environment
RUN uv sync --frozen --no-install-project --no-dev

# Use the virtual environment
ENV PATH="/venv/bin:$PATH"

# Copy the application
COPY app /code/




# Install boto3 for AWS S3 integration
# RUN pip install boto3

ENV PYTHONPATH=/code
EXPOSE 8000