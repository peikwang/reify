#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

HOST="${1:-root@117.148.166.55}"
PORT="${2:-12888}"
IMAGE="${VIBEFORGE_IMAGE:-vllm/vllm-openai:latest}"
APP_IMAGE="${VIBEFORGE_APP_IMAGE:-vibeforge-app:latest}"
CADDY_IMAGE="${VIBEFORGE_CADDY_IMAGE:-caddy:2.10.2-alpine}"
NAME="${VIBEFORGE_CONTAINER:-vibeforge}"
SANDBOX_NAME="${VIBEFORGE_SANDBOX_NAME:-vibeforge-sandbox}"
SANDBOX_SERVER_IMAGE="${VIBEFORGE_SANDBOX_SERVER_IMAGE:-opensandbox/server:release-1.1.1}"
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
  --exclude='frontend/node_modules' \
  --exclude='web/dist' \
  --exclude='.auth.env' \
  --exclude='.sandbox.env' \
  --exclude='.llm.env' \
  --exclude='.runtime.env' \
  --exclude='tests/*.png' \
  . | ssh "$HOST" 'mkdir -p /opt/vibeforge && tar xzf - -C /opt/vibeforge'

echo "→ building app image ${APP_IMAGE}"
ssh "$HOST" "cd /opt/vibeforge && docker build -q -t ${APP_IMAGE} --build-arg BASE_IMAGE=${IMAGE} -f Dockerfile.app ."

echo "→ publishing frontend build from image"
ssh "$HOST" "mkdir -p /opt/vibeforge/web/dist
cid=\$(docker create ${APP_IMAGE})
docker cp \$cid:/app/web/dist/. /opt/vibeforge/web/dist/
docker rm \$cid >/dev/null
chmod -R a+rX /opt/vibeforge/web/dist"

echo "→ ensuring access credentials"
ssh "$HOST" '
  if [ ! -s /opt/vibeforge/.auth.env ]; then
    umask 077
    {
      echo "VIBEFORGE_ADMIN_USER=admin"
      echo "VIBEFORGE_ADMIN_PASSWORD=$(openssl rand -hex 12)"
      echo "VIBEFORGE_COOKIE_SECURE=1"
      echo "VIBEFORGE_REGISTRATION=open"
    } > /opt/vibeforge/.auth.env
  fi
  chmod 600 /opt/vibeforge/.auth.env

  if [ ! -s /opt/vibeforge/.sandbox.env ]; then
    umask 077
    {
      echo "VIBEFORGE_SANDBOX=opensandbox"
      echo "VIBEFORGE_SANDBOX_DOMAIN=vibeforge-sandbox:8080"
      echo "VIBEFORGE_SANDBOX_API_KEY=$(openssl rand -hex 24)"
      echo "VIBEFORGE_SANDBOX_SERVER_PROXY=1"
      echo "VIBEFORGE_SANDBOX_IMAGE=node:24-bookworm-slim"
      # This Docker host cannot start the egress sidecar; use open until supported.
      echo "VIBEFORGE_SANDBOX_EGRESS=open"
      echo "VIBEFORGE_SANDBOX_BUILD_MEMORY=4Gi"
      echo "VIBEFORGE_SANDBOX_HOST_DATA_ROOT=/opt/vibeforge/data/users"
      echo "VIBEFORGE_SSR_PREVIEW=1"
      echo "VIBEFORGE_SSR_PORT=12889"
    } > /opt/vibeforge/.sandbox.env
  fi
  chmod 600 /opt/vibeforge/.sandbox.env
  for line in \
    "VIBEFORGE_SANDBOX_BUILD_MEMORY=4Gi" \
    "VIBEFORGE_SANDBOX_HOST_DATA_ROOT=/opt/vibeforge/data/users" \
    "VIBEFORGE_SSR_PREVIEW=1" \
    "VIBEFORGE_SSR_PORT=12889"; do
    key=${line%%=*}
    grep -q "^${key}=" /opt/vibeforge/.sandbox.env || echo "$line" >> /opt/vibeforge/.sandbox.env
  done
  mkdir -p /opt/vibeforge/data/users

  {
    cat /opt/vibeforge/.auth.env
    if [ -s /opt/vibeforge/.llm.env ]; then cat /opt/vibeforge/.llm.env; fi
    cat /opt/vibeforge/.sandbox.env
  } > /opt/vibeforge/.runtime.env
  chmod 600 /opt/vibeforge/.runtime.env
'

echo "→ replacing platform containers (sandbox is kept)"
ssh "$HOST" "docker rm -f ${NAME}-caddy 2>/dev/null || true
docker rm -f ${NAME} 2>/dev/null || true
docker network inspect vibeforge-net >/dev/null 2>&1 || docker network create vibeforge-net"

echo "→ backing up local database"
ssh "$HOST" 'umask 077
if [ -f /opt/vibeforge/data/vibeforge.db ]; then
  mkdir -p /opt/vibeforge/backups
  chmod 700 /opt/vibeforge/backups
  stamp=$(date +%Y%m%d-%H%M%S)
  cp /opt/vibeforge/data/vibeforge.db "/opt/vibeforge/backups/vibeforge-$stamp.db"
  [ -f /opt/vibeforge/data/vibeforge.db-wal ] && cp /opt/vibeforge/data/vibeforge.db-wal "/opt/vibeforge/backups/vibeforge-$stamp.db-wal"
  [ -f /opt/vibeforge/data/vibeforge.db-shm ] && cp /opt/vibeforge/data/vibeforge.db-shm "/opt/vibeforge/backups/vibeforge-$stamp.db-shm"
  chmod 600 /opt/vibeforge/backups/vibeforge-$stamp.*
fi'

echo "→ configuring OpenSandbox"
ssh "$HOST" '
  mkdir -p /opt/vibeforge/sandbox
  chmod 700 /opt/vibeforge/sandbox
  KEY=$(grep "^VIBEFORGE_SANDBOX_API_KEY=" /opt/vibeforge/.sandbox.env | cut -d= -f2-)
  GATEWAY=$(docker network inspect bridge -f "{{(index .IPAM.Config 0).Gateway}}" 2>/dev/null || true)
  [ -n "$GATEWAY" ] || GATEWAY=172.17.0.1
  cat > /opt/vibeforge/sandbox/config.toml <<EOF
[server]
host = "0.0.0.0"
port = 8080
max_sandbox_timeout_seconds = 3600
api_key = "$KEY"

[proxy]
resolve_internal = true

[log]
level = "INFO"

[runtime]
type = "docker"
execd_image = "opensandbox/execd:v1.1.0"

[storage]
allowed_host_paths = ["/opt/vibeforge/data/users"]

[store]
type = "sqlite"
path = "/opt/opensandbox/opensandbox.db"

[docker]
network_mode = "bridge"
port_range_min = 41000
port_range_max = 42000
publish_host = "$GATEWAY"
drop_capabilities = ["AUDIT_WRITE", "MKNOD", "NET_ADMIN", "NET_RAW", "SYS_ADMIN", "SYS_MODULE", "SYS_PTRACE", "SYS_TIME", "SYS_TTY_CONFIG"]
no_new_privileges = true
pids_limit = 4096

[ingress]
mode = "direct"

[egress]
image = "opensandbox/egress:v1.1.7"
mode = "dns"
readiness_timeout_seconds = 30.0
EOF
  chmod 600 /opt/vibeforge/sandbox/config.toml
'

echo "→ ensuring ${SANDBOX_NAME}"
ssh "$HOST" "
if docker inspect ${SANDBOX_NAME} >/dev/null 2>&1; then
  echo 'sandbox container exists; keeping it'
  docker start ${SANDBOX_NAME} >/dev/null 2>&1 || true
fi
if ! docker inspect ${SANDBOX_NAME} >/dev/null 2>&1; then
  docker run -d --name ${SANDBOX_NAME} --restart unless-stopped \
    --network vibeforge-net --network-alias vibeforge-sandbox \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /opt/vibeforge/sandbox:/opt/opensandbox \
    --add-host=host.docker.internal:host-gateway \
    ${SANDBOX_SERVER_IMAGE} --config /opt/opensandbox/config.toml
fi"

i=0
while [ "$i" -lt 10 ]; do
  docker network connect bridge ${SANDBOX_NAME} 2>/dev/null && break
  i=$((i + 1))
  /bin/sleep 1
done

i=0
while [ "$i" -lt 20 ]; do
  RUNNING=$(ssh "$HOST" "docker inspect -f '{{.State.Running}}' ${SANDBOX_NAME} 2>/dev/null || true")
  if [ "$RUNNING" = "true" ]; then break; fi
  i=$((i + 1))
  /bin/sleep 1
done
if [ "$RUNNING" != "true" ]; then
  echo "⚠ sandbox server is not running; static projects still work"
  ssh "$HOST" "docker logs --tail 40 ${SANDBOX_NAME}" || true
fi

echo "→ starting ${NAME} (internal only)"
ssh "$HOST" "docker run -d --name ${NAME} --restart unless-stopped \
  --network vibeforge-net --network-alias vibeforge \
  -v /opt/vibeforge:/app -w /app \
  --add-host=host.docker.internal:host-gateway \
  --env-file /opt/vibeforge/.runtime.env \
  --entrypoint python3 \
  ${APP_IMAGE} \
  -m uvicorn server.main:app --host 0.0.0.0 --port ${PORT}"

echo "→ starting Caddy TLS on :${PORT} (HTTP :80 for ACME, SSR :12889)"
ssh "$HOST" "docker run -d --name ${NAME}-caddy --restart unless-stopped \
  --network vibeforge-net \
  -p ${PORT}:${PORT} -p 12889:12889 -p 80:80 \
  -e VIBEFORGE_HOST_IP=${HOST_IP} \
  -e VIBEFORGE_SSR_PORT=12889 \
  -v /opt/vibeforge/Caddyfile:/etc/caddy/Caddyfile:ro \
  -v ${NAME}-caddy-data:/data \
  -v ${NAME}-caddy-config:/config \
  ${CADDY_IMAGE}"

echo "→ waiting for HTTPS health"
i=0
while [ "$i" -lt 60 ]; do
  if ssh "$HOST" "curl -kfsS --resolve ${HOST_IP}:${PORT}:127.0.0.1 https://${HOST_IP}:${PORT}/api/health >/dev/null 2>&1"; then
    CODE=$(ssh "$HOST" "curl -ks -o /dev/null -w '%{http_code}' --resolve ${HOST_IP}:${PORT}:127.0.0.1 https://${HOST_IP}:${PORT}/api/projects")
    if [ "$CODE" != "401" ]; then
      echo "✗ auth gate is not active (got ${CODE})"
      exit 1
    fi
    HEALTH=$(ssh "$HOST" "curl -kfsS --resolve ${HOST_IP}:${PORT}:127.0.0.1 https://${HOST_IP}:${PORT}/api/health")
    echo "$HEALTH"
    if echo "$HEALTH" | grep -q '"backend":"opensandbox"' && ! echo "$HEALTH" | grep -q '"reachable":true'; then
      echo "⚠ sandbox backend is configured but unreachable; React builds will fail"
    fi
    echo
    echo "✓ https://${HOST_IP}:${PORT}/"
    echo "  credentials: ${HOST}:/opt/vibeforge/.auth.env"
    echo "  sandbox:     ${HOST}:/opt/vibeforge/.sandbox.env"
    echo "  SSR apps:    https://${HOST_IP}:12889/apps/<project>/ (open 12889 in the firewall)"
    exit 0
  fi
  i=$((i + 1))
  /bin/sleep 1
done

echo "✗ health check failed; logs:"
ssh "$HOST" "docker logs --tail 80 ${NAME}-caddy" || true
ssh "$HOST" "docker logs --tail 40 ${NAME}" || true
exit 1
