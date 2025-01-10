# make a dockerfile for python 3.13 with the following requirements
# 1. Use the official Python 3.13-slim-buster image
# 2. Set the working directory to /curly-disco
# 3. Copy the current directory to /app
# 4. Add a healthcheck to determine if the container is healthy
# 5. Set the default command to python3
# 6. Build the image with the tag python-curly-disco
# 7. Run the container with the name curly-disco
# 8. Make the container restart unless-stopped


FROM python:3.13-bookworm

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    # Poetry's configuration:
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR='/var/cache/pypoetry' \
    POETRY_HOME='/usr/local' \
    POETRY_VERSION=1.8.5

# Install Poetry - respects $POETRY_VERSION & $POETRY_HOME
RUN curl -sSL https://install.python-poetry.org | python3 - 

WORKDIR /app
COPY poetry.lock pyproject.toml /app/
RUN poetry install --no-interaction --no-ansi --only=main

COPY ./curly-disco/ /app
HEALTHCHECK --interval=60s --timeout=3s CMD curl -f http://localhost:8080 || exit 1

CMD ["echo", "container is up"]

# docker build -t python-curly-disco .
