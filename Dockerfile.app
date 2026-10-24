ARG BASE_IMAGE=vllm/vllm-openai:latest

FROM node:24-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run typecheck && npm run build

FROM ${BASE_IMAGE}

COPY requirements.txt /tmp/vibeforge-requirements.txt
RUN pip install --no-cache-dir -r /tmp/vibeforge-requirements.txt

ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=frontend /web/dist /app/web/dist
