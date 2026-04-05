FROM public.ecr.aws/lambda/python:3.12

# Install system dependencies for OpenCV
RUN dnf install -y mesa-libGL && dnf clean all

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv pip install --system --no-cache .

# Copy source code
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# Set Python path so imports work
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}/src"

# Lambda handler
CMD ["api.main.handler"]
