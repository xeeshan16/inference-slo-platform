# syntax=docker/dockerfile:1.7
ARG PYTHON_IMAGE=python:3.12.15-slim-bookworm

# --- Stage 1: train the model and export it to ONNX -------------------------
FROM ${PYTHON_IMAGE} AS trainer
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements-train.txt .
RUN pip install -r requirements-train.txt
COPY training/ training/
RUN python -m training.train --out /build/model

# --- Stage 2: install runtime dependencies into a virtualenv ----------------
FROM ${PYTHON_IMAGE} AS deps
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
COPY requirements.txt .
RUN /opt/venv/bin/pip install -r requirements.txt

# --- Stage 3: runtime --------------------------------------------------------
FROM ${PYTHON_IMAGE}
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_DIR=/app/model
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --no-create-home app
WORKDIR /app
COPY --from=deps /opt/venv /opt/venv
COPY --from=trainer /build/model /app/model
COPY app/ app/
RUN python -m compileall -q /app/app
USER 10001:10001
EXPOSE 8080
ENTRYPOINT ["python", "-m", "app"]
