# Multi-stage Dockerfile for OpenExec Orchestration
# Python 3.11+ AI Planning Engine

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir build

# Copy source code
COPY src/ ./src/
COPY README.md ./

# Build and install the package
RUN pip install --no-cache-dir .

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

# Create non-root user
RUN groupadd --gid 1000 openexec && \
    useradd --uid 1000 --gid openexec --shell /bin/bash --create-home openexec

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create project mount point
RUN mkdir -p /project && chown openexec:openexec /project
WORKDIR /project

USER openexec

ENTRYPOINT ["python", "-m", "openexec_planner"]
CMD ["--help"]
