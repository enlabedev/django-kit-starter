FROM python:3.12-slim

ENV POETRY_NO_INTERACTION=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    libpq-dev \
    curl \
    python3-magic \
    libpango-1.0-0 libcairo2 libffi-dev libpangoft2-1.0-0 \
    libmagic1 \
    gettext \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/etc/poetry python3 -
RUN chmod +x /etc/poetry/bin/poetry
RUN /etc/poetry/bin/poetry config virtualenvs.create false
COPY pyproject.toml poetry.lock ./
RUN /etc/poetry/bin/poetry install --no-root

COPY . /app/

EXPOSE 8000
