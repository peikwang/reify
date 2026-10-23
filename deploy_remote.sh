#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

HOST="${1:-root@117.148.166.55}"
PORT="${2:-12888}"
IMAGE="${VIBEFORGE_IMAGE:-vllm/vllm-openai:latest}"
CADDY_IMAGE="${VIBEFORGE_CADDY_IMAGE:-caddy:2.10.2-alpine}"
NAME="${VIBEFORGE_CONTAINER:-vibeforge}"
HOST_IP="${HOST#*@}"

if [ "$PORT" != "12888" ]; then
  echo "Caddyfile currently supports only port 12888; got ${PORT}" >&2
  exit 1
fi

echo "→ syncing source to ${HOST}:/opt/vibeforge"
COPYFILE_DISABLE=1 tar czf - \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='projects' \
  --exclude='data' \
  --exclude='.auth.env' \
  --exclude='.llm.env' \
  --exclude='.runtime.env' \
  --exclude='tests/*.png' \
  . | ssh "$HOST" 'mkdir -p /opt/vibeforge && tar xzf - -C /opt/vibeforge'

echo "→ ensuring access credentials"
ssh "$HOST" '
  if [ ! -s /opt/vibeforge/.auth.env ]; then
    umask 077
    {
      echo "VIBEFORGE_PASSWORD=$(openssl rand -hex 12)"
      echo "VIBEFORGE_SECRET=$(openssl rand -hex 32)"
      echo "VIBEFORGE_COOKIE_SECURE=1"
    } > /opt/vibeforge/.auth.env
  fi
  chmod 600 /opt/vibeforge/.auth.env
  if [ -s /opt/vibeforge/.llm.env ]; then
    cat /opt/vibeforge/.auth.env /opt/vibeforge/.llm.env > /opt/vibeforge/.runtime.env
  else
    cp /opt/vibeforge/.auth.env /opt/vibeforge/.runtime.env
  fi
  chmod 600 /opt/vibeforge/.runtime.env
'

echo "→ preparing HTTPS network"
ssh "$HOST" "docker rm -f ${NAME}-caddy 2>/dev/null || true
docker rm -f ${NAME} 2>/dev/null || true
docker network inspect vibeforge-net >/dev/null 2>&1 || docker network create vibeforge-net"

echo "→ starting ${NAME} (internal only)"
ssh "$HOST" "docker run -d --name ${NAME} --restart unless-stopped \
  --network vibeforge-net --network-alias vibeforge \
  -v /opt/vibeforge:/app -w /app \
  --add-host=host.docker.internal:host-gateway \
  --env-file /opt/vibeforge/.runtime.env \
  --entrypoint python3 \
  ${IMAGE} \
  -m uvicorn server.main:app --host 0.0.0.0 --port ${PORT}"

echo "→ starting Caddy TLS on :${PORT} (HTTP :80 for ACME)"
ssh "$HOST" "docker run -d --name ${NAME}-caddy --restart unless-stopped \
  --network vibeforge-net \
  -p ${PORT}:${PORT} -p 80:80 \
  -e VIBEFORGE_HOST_IP=${HOST_IP} \
  -v /opt/vibeforge/Caddyfile:/etc/caddy/Caddyfile:ro \
  -v ${NAME}-caddy-data:/data \
  -v ${NAME}-caddy-config:/config \
  ${CADDY_IMAGE}"

echo "→ waiting for HTTPS health"
i=0
while [ "$i" -lt 60 ]; do
  if ssh "$HOST" "curl -kfsS --resolve ${HOST_IP}:${PORT}:127.0.0.1 https://${HOST_IP}:${PORT}/api/health >/dev/null 2>&1"; then
    CODE=$(ssh "$HOST" "curl -ks -o /dev/null -w '%{http_code}' --resolve ${HOST_IP}:${PORT}:127.0.0.1 https://${HOST_IP}:${PORT}/api/tasks")
    if [ "$CODE" != "401" ]; then
      echo "✗ auth gate is not active (got ${CODE})"
      exit 1
    fi
    ssh "$HOST" "curl -kfsS --resolve ${HOST_IP}:${PORT}:127.0.0.1 https://${HOST_IP}:${PORT}/api/health"
    echo
    echo "✓ https://${HOST_IP}:${PORT}/"
    echo "  credentials: ${HOST}:/opt/vibeforge/.auth.env"
    exit 0
  fi
  i=$((i + 1))
  /bin/sleep 1
done

echo "✗ health check failed; logs:"
ssh "$HOST" "docker logs --tail 80 ${NAME}-caddy" || true
ssh "$HOST" "docker logs --tail 40 ${NAME}" || true
exit 1
