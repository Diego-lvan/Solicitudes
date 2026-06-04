# syntax=docker/dockerfile:1.7

# ---- Stage 1: builder -------------------------------------------------------
FROM python:3.13.13-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# OS deps for WeasyPrint, Postgres client headers, building wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libcairo2 \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        shared-mime-info \
        fonts-dejavu \
        fonts-liberation \
        libpq-dev \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app/requirements.txt app/requirements-dev.txt /app/
RUN pip install -r requirements.txt -r requirements-dev.txt

# ---- Stage 2: runtime -------------------------------------------------------
FROM python:3.13.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        libcairo2 \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        shared-mime-info \
        fonts-dejavu \
        fonts-liberation \
        libpq5 \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app

# Tailwind standalone CLI binary (no Node required).
ARG TAILWIND_VERSION=4.2.4
ARG TARGETARCH
RUN case "${TARGETARCH}" in \
        amd64) TW_ARCH=x64 ;; \
        arm64) TW_ARCH=arm64 ;; \
        *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac \
    && curl -sSL -o /usr/local/bin/tailwindcss \
        "https://github.com/tailwindlabs/tailwindcss/releases/download/v${TAILWIND_VERSION}/tailwindcss-linux-${TW_ARCH}" \
    && chmod +x /usr/local/bin/tailwindcss

COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app
COPY --chown=app:app app/ /app/

# Build the production Tailwind bundle inside the image. app.build.css is
# gitignored, so we regenerate it here to keep the build self-contained.
RUN tailwindcss -i /app/static/css/app.css \
                 -o /app/static/css/app.build.css --minify

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# WORKDIR creates /app as root; collectstatic/uploads need the app user to own
# it and the generated dirs. Create them up front and hand the tree to `app`.
RUN mkdir -p /app/staticfiles /app/media && chown -R app:app /app

# NOTE: we intentionally do NOT `USER app` here. The entrypoint starts as root
# so it can chown the (root-owned) mounted volume, then gunicorn drops worker
# privileges to the `app` user via --user/--group.

EXPOSE 8000

CMD ["docker-entrypoint.sh"]
