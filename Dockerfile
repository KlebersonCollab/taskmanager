FROM python:3.11-slim

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Configure Python and uv environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# Copy dependency definition
COPY pyproject.toml /app/

# Copy source code and example modules
COPY taskmanager/ /app/taskmanager/
COPY example_tasks.py enqueue_examples.py README.md /app/
COPY scripts/ /app/scripts/

# Install dependencies and taskmanager package
RUN uv pip install --no-cache -e .

# Expose default dashboard port
EXPOSE 8000

# Default entrypoint
CMD ["taskmanager", "dev", "--host", "0.0.0.0", "--port", "8000", "--modules", "example_tasks"]
