FROM ghcr.io/astral-sh/uv:python3.13-alpine

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# Prepare the environment
COPY pyproject.toml uv.lock /app/
RUN uv sync --locked --no-cache
# Add the application code
COPY ./curly-disco/ /app

HEALTHCHECK --interval=60s --timeout=3s CMD curl -f http://localhost:8080 || exit 1

CMD ["uv", "run"]

# docker build -t python-curly-disco .
