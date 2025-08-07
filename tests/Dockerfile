# Use miniconda base image to match GitHub Actions setup
FROM continuumio/miniconda3:latest@sha256:4a2425c3ca891633e5a27280120f3fb6d5960a0f509b7594632cdd5bb8cbaea8

# Set working directory
WORKDIR /workspace

# Copy the project files
COPY . /workspace/

# Initialize conda for bash shell (following GitHub Actions pattern)
RUN conda init bash

# Install dependencies following exact GitHub Actions pattern
SHELL ["/bin/bash", "-l", "-c"]
RUN conda install \
    --yes \
    --file tests/requirements.txt \
    --file tests/requirements-ci.txt \
    python=3.11 \
    --channel defaults

# Install the package in development mode (following GitHub Actions pattern)
RUN pip install -e .

# Set default environment variables (pytest-docker-tools will override as needed)
ENV CI=true

# Default command for the container (pytest-docker-tools will override this)
CMD ["/bin/bash", "-l"]
