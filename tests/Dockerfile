# Use miniconda base image to match GitHub Actions setup
FROM continuumio/miniconda3:latest@sha256:1808b31ef43e9c521cde5884ba4df9ec26d8d503a314cea787590f8550358a63

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
