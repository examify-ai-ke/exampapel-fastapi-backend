FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11-slim
ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=100
WORKDIR /code
# Install Poetry
RUN apt clean && apt update && apt install curl -y
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

# Copy poetry.lock* in case it doesn't exist in the repo
COPY app/pyproject.toml app/poetry.lock* /code/
# COPY alembic.ini /code/
# COPY app/requirements.txt /code/
# Allow installing dev dependencies to run tests
ARG INSTALL_DEV=false
# RUN pip install -r requirements.txt
RUN bash -c "if [ $INSTALL_DEV == 'true' ] ; then poetry install --no-root ; else poetry install --no-root --only main ; fi"

# Install boto3 for AWS S3 integration
# RUN pip install boto3

ENV PYTHONPATH=/code
EXPOSE 8000