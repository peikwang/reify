ARG BASE_IMAGE=vllm/vllm-openai:latest
FROM ${BASE_IMAGE}

COPY requirements.txt /tmp/vibeforge-requirements.txt
RUN pip install --no-cache-dir -r /tmp/vibeforge-requirements.txt

ENV PYTHONUNBUFFERED=1
WORKDIR /app
