# Build stage: install pixi and create environment
FROM ghcr.io/prefix-dev/pixi:0.76.1 AS builder

WORKDIR /app

# Copy pixi files first for better caching
COPY pixi.toml pixi.lock ./

# Install dependencies (creates .pixi directory)
RUN pixi install --locked

# Runtime stage: minimal image with the environment
FROM debian:bookworm-slim

# Install minimal runtime dependencies
RUN apt-get update -q && \
    apt-get install -q -y --no-install-recommends \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the pixi environment from builder
COPY --from=builder /app/.pixi /app/.pixi

# Copy application code
COPY app/ ./app/

# Set environment to use pixi's Python
ENV PATH="/app/.pixi/envs/default/bin:${PATH}"
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
