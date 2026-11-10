FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=180 \
    UV_NO_CACHE=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations
COPY oasis_engine_runtime /opt/pakar/oasis_engine_runtime

FROM base AS production

RUN apt-get update && \
    apt-get install --yes --no-install-recommends gcc libc6-dev libcairo2 && \
    rm -rf /var/lib/apt/lists/* && \
    pip install ".[llm,firebase]" uv==0.13.6 && \
    uv sync --project /opt/pakar/oasis_engine_runtime --locked --no-dev && \
    groupadd --gid 10001 pakar && \
    useradd --uid 10001 --gid pakar --create-home pakar && \
    mkdir -p /app/data /opt/pakar/oasis_engine_runtime/logs && \
    chown -R pakar:pakar /app /opt/pakar/oasis_engine_runtime/logs

COPY run.py ./run.py
COPY worker.py ./worker.py

USER pakar
EXPOSE 5001

CMD ["python", "run.py"]

FROM base AS test

RUN pip install ".[test]"
COPY tests ./tests

CMD ["python", "-m", "pytest", "-vv"]
