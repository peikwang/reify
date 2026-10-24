#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

HOST="${1:-root@117.148.166.55}"
PORT="${2:-12888}"
IMAGE="${REIFY_IMAGE:-python:3.12-slim}"
APP_IMAGE="${REIFY_APP_IMAGE:-reify-app:latest}"
CADDY_IMAGE="${REIFY_CADDY_IMAGE:-caddy:2.10.2-alpine}"
NAME="${REIFY_CONTAINER:-reify}"
SANDBOX_NAME="${REIFY_SANDBOX_NAME:-reify-sandbox}"
SANDBOX_SERVER_IMAGE="${REIFY_SANDBOX_SERVER_IMAGE:-opensandbox/server:release-1.1.1}"
HOST_IP="${HOST#*@}"

if [ "$PORT" != "12888" ]; then
  echo "Caddyfile currently supports only port 12888; got ${PORT}" >&2
  exit 1
fi

echo "→ migrating /opt/reify to /data/reify-deploy (one time)"
ssh "$HOST" 'set -e
OLD=/opt/reify
NEW=/data/reify-deploy
if [ -d "$OLD" ] && [ ! -f "$NEW/.migrated" ]; then
  AVAIL=$(df -Pk /data | sed -n "2p" | tr -s " " | cut -d" " -f4)
  NEED=$(du -sk "$OLD" | cut -f1)
  if [ "$AVAIL" -lt "$NEED" ]; then
    echo "✗ not enough space on /data: avail=${AVAIL}KB need=${NEED}KB" >&2
    exit 1
  fi
  mkdir -p "$NEW"
  WAS_RUNNING=$(docker inspect -f '{{.State.Running}}' reify 2>/dev/null || echo false)
  docker stop reify >/dev/null 2>&1 || true
  if ! rsync -aHAX "$OLD/" "$NEW/"; then
    [ "$WAS_RUNNING" = "true" ] && docker start reify >/dev/null 2>&1 || true
    exit 1
  fi
  [ "$WAS_RUNNING" = "true" ] && docker start reify >/dev/null 2>&1 || true
  touch "$NEW/.migrated"
  echo "migrated /opt/reify -> $NEW"
fi'

echo "→ syncing source to ${HOST}:/data/reify-deploy"
COPYFILE_DISABLE=1 tar czf - \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='projects' \
  --exclude='data' \
  --exclude='backups' \
  --exclude='.pytest_cache' \
  --exclude='.env' \
  --exclude='frontend/node_modules' \
  --exclude='frontend/dist' \
  --exclude='web/dist' \
  --exclude='.auth.env' \
  --exclude='.sandbox.env' \
  --exclude='.llm.env' \
  --exclude='.runtime.env' \
  --exclude='tests/*.png' \
  . | ssh "$HOST" 'mkdir -p /data/reify-deploy && tar xzf - -C /data/reify-deploy'

echo "→ building app image ${APP_IMAGE}"
ssh "$HOST" "cd /data/reify-deploy && docker build -q -t ${APP_IMAGE} --build-arg BASE_IMAGE=${IMAGE} -f Dockerfile.app ."

echo "→ publishing frontend build from image"
ssh "$HOST" "set -e
mkdir -p /data/reify-deploy/web/dist
cid=\$(docker create ${APP_IMAGE})
docker cp \$cid:/app/web/dist/. /data/reify-deploy/web/dist/
docker rm \$cid >/dev/null
chmod -R a+rX /data/reify-deploy/web/dist
test -f /data/reify-deploy/web/dist/index.html
grep -q 'id=\"root\"' /data/reify-deploy/web/dist/index.html"

echo "→ migrating legacy /opt/vibeforge (one time)"
ssh "$HOST" 'set -e
OLD=/opt/vibeforge
NEW=/data/reify-deploy
if [ -d "$OLD" ] && [ ! -d "$NEW/data" ]; then
  mkdir -p "$NEW/data"
  if docker inspect vibeforge >/dev/null 2>&1; then
    docker exec vibeforge python3 -c "import sqlite3; s=sqlite3.connect(\"/app/data/vibeforge.db\"); d=sqlite3.connect(\"/app/data/reify.db\"); c=s.cursor(); c.execute(\"update runtimes set status=\x27stopped\x27, endpoint=NULL\"); s.commit(); s.backup(d); d.close(); s.close()" || true
  fi
  cp -a "$OLD/data/." "$NEW/data/"
  if [ -f "$NEW/data/vibeforge.db" ] && [ ! -f "$NEW/data/reify.db" ]; then
    mv "$NEW/data/vibeforge.db" "$NEW/data/reify.db"
  fi
  for file in .auth.env .sandbox.env .llm.env; do
    if [ -f "$OLD/$file" ] && [ ! -f "$NEW/$file" ]; then
      sed "s/^VIBEFORGE_/REIFY_/" "$OLD/$file" > "$NEW/$file"
      chmod 600 "$NEW/$file"
    fi
  done
  echo "legacy data migrated"
else
  echo "legacy migration skipped (already migrated or no old install)"
fi'

echo "→ ensuring access credentials"
ssh "$HOST" '
  if [ ! -s /data/reify-deploy/.auth.env ]; then
    umask 077
    {
      echo "REIFY_ADMIN_USER=admin"
      echo "REIFY_ADMIN_PASSWORD=$(openssl rand -hex 12)"
      echo "REIFY_COOKIE_SECURE=1"
      echo "REIFY_REGISTRATION=open"
    } > /data/reify-deploy/.auth.env
  fi
  chmod 600 /data/reify-deploy/.auth.env

  if [ ! -s /data/reify-deploy/.sandbox.env ]; then
    umask 077
    {
      echo "REIFY_SANDBOX=opensandbox"
      echo "REIFY_PROJECTS=/data/reify-deploy/data/projects"
      echo "REIFY_SANDBOX_DOMAIN=reify-sandbox:8080"
      echo "REIFY_SANDBOX_API_KEY=$(openssl rand -hex 24)"
      echo "REIFY_SANDBOX_SERVER_PROXY=1"
      echo "REIFY_SANDBOX_IMAGE=node:24-bookworm-slim"
      # This Docker host cannot start the egress sidecar; use open until supported.
      echo "REIFY_SANDBOX_EGRESS=open"
      echo "REIFY_SANDBOX_BUILD_MEMORY=4Gi"
      echo "REIFY_SANDBOX_HOST_DATA_ROOT=/data/reify-deploy/data/users"
      echo "REIFY_SANDBOX_REQUEST_TIMEOUT=900"
      echo "REIFY_NPM_INSTALL_TIMEOUT=600"
      echo "REIFY_NPM_BUILD_TIMEOUT=600"
      echo "REIFY_SSR_PREVIEW=1"
      echo "REIFY_SSR_PORT=12889"
    } > /data/reify-deploy/.sandbox.env
  fi
  chmod 600 /data/reify-deploy/.sandbox.env
  for line in \
    "REIFY_PROJECTS=/data/reify-deploy/data/projects" \
    "REIFY_SANDBOX_DOMAIN=reify-sandbox:8080" \
    "REIFY_SANDBOX_BUILD_MEMORY=4Gi" \
    "REIFY_SANDBOX_HOST_DATA_ROOT=/data/reify-deploy/data/users" \
    "REIFY_SANDBOX_REQUEST_TIMEOUT=900" \
    "REIFY_NPM_INSTALL_TIMEOUT=600" \
    "REIFY_NPM_BUILD_TIMEOUT=600" \
    "REIFY_SSR_PREVIEW=1" \
    "REIFY_SSR_PORT=12889"; do
    key=${line%%=*}
    sed -i "/^${key}=/d" /data/reify-deploy/.sandbox.env
    echo "$line" >> /data/reify-deploy/.sandbox.env
  done
  mkdir -p /data/reify-deploy/data/users /data/reify-deploy/data/projects

  {
    cat /data/reify-deploy/.auth.env
    if [ -s /data/reify-deploy/.llm.env ]; then cat /data/reify-deploy/.llm.env; fi
    cat /data/reify-deploy/.sandbox.env
  } > /data/reify-deploy/.runtime.env
  chmod 600 /data/reify-deploy/.runtime.env
'

echo "→ backing up local database"
ssh "$HOST" 'umask 077
if [ -f /data/reify-deploy/data/reify.db ]; then
  mkdir -p /data/reify-deploy/backups
  chmod 700 /data/reify-deploy/backups
  stamp=$(date +%Y%m%d-%H%M%S)
  cp /data/reify-deploy/data/reify.db "/data/reify-deploy/backups/reify-$stamp.db"
  [ -f /data/reify-deploy/data/reify.db-wal ] && cp /data/reify-deploy/data/reify.db-wal "/data/reify-deploy/backups/reify-$stamp.db-wal"
  [ -f /data/reify-deploy/data/reify.db-shm ] && cp /data/reify-deploy/data/reify.db-shm "/data/reify-deploy/backups/reify-$stamp.db-shm"
  chmod 600 /data/reify-deploy/backups/reify-$stamp.*
fi'

echo "→ replacing platform containers (sandbox is kept)"
ssh "$HOST" "docker rm -f ${NAME}-caddy 2>/dev/null || true
docker rm -f ${NAME} 2>/dev/null || true
docker rm -f vibeforge-caddy 2>/dev/null || true
docker rm -f vibeforge 2>/dev/null || true
docker network inspect reify-net >/dev/null 2>&1 || docker network create reify-net"

echo "→ configuring OpenSandbox"
ssh "$HOST" '
  mkdir -p /data/reify-deploy/sandbox
  chmod 700 /data/reify-deploy/sandbox
  KEY=$(grep "^REIFY_SANDBOX_API_KEY=" /data/reify-deploy/.sandbox.env | cut -d= -f2-)
  GATEWAY=$(docker network inspect bridge -f "{{(index .IPAM.Config 0).Gateway}}" 2>/dev/null || true)
  [ -n "$GATEWAY" ] || GATEWAY=172.17.0.1
  cat > /data/reify-deploy/sandbox/config.toml <<EOF
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
allowed_host_paths = ["/data/reify-deploy/data/users"]

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
  chmod 600 /data/reify-deploy/sandbox/config.toml
'

echo "→ ensuring ${SANDBOX_NAME}"
ssh "$HOST" "
docker rm -f ${SANDBOX_NAME} >/dev/null 2>&1 || true
if ! docker inspect ${SANDBOX_NAME} >/dev/null 2>&1; then
  docker run -d --name ${SANDBOX_NAME} --restart unless-stopped \
    --network reify-net --network-alias reify-sandbox \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /data/reify-deploy/sandbox:/opt/opensandbox \
    --add-host=host.docker.internal:host-gateway \
    ${SANDBOX_SERVER_IMAGE} --config /opt/opensandbox/config.toml
fi"

if ! ssh "$HOST" "docker inspect -f '{{json .NetworkSettings.Networks}}' ${SANDBOX_NAME} | grep -q '\"bridge\"'"; then
  ssh "$HOST" "docker network connect bridge ${SANDBOX_NAME}" || true
fi

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
  --network reify-net --network-alias reify \
  -v /data/reify-deploy:/app -w /app \
  --add-host=host.docker.internal:host-gateway \
  --cpus 2 --memory 4g --pids-limit 512 \
  --cap-drop ALL --security-opt no-new-privileges \
  --env-file /data/reify-deploy/.runtime.env \
  --entrypoint python3 \
  ${APP_IMAGE} \
  -m uvicorn server.main:app --host 0.0.0.0 --port ${PORT}"

echo "→ starting Caddy TLS on :${PORT} (HTTP :80 for ACME, SSR :12889)"
ssh "$HOST" "docker run -d --name ${NAME}-caddy --restart unless-stopped \
  --network reify-net \
  -p ${PORT}:${PORT} -p 12889:12889 -p 80:80 \
  -e REIFY_HOST_IP=${HOST_IP} \
  -e REIFY_SSR_PORT=12889 \
  -v /data/reify-deploy/Caddyfile:/etc/caddy/Caddyfile:ro \
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
    UI_CODE=$(ssh "$HOST" "curl -ks -o /dev/null -w '%{http_code}' --resolve ${HOST_IP}:${PORT}:127.0.0.1 https://${HOST_IP}:${PORT}/login")
    if [ "$UI_CODE" != "200" ]; then
      echo "✗ React UI did not load (got ${UI_CODE})"
      exit 1
    fi
    if ! ssh "$HOST" "curl -kfsS --resolve ${HOST_IP}:${PORT}:127.0.0.1 https://${HOST_IP}:${PORT}/login | grep -q 'id=\"root\"'"; then
      echo "✗ React UI index is missing the root mount"
      exit 1
    fi
    if echo "$HEALTH" | grep -q '"backend":"opensandbox"' && ! echo "$HEALTH" | grep -q '"reachable":true'; then
      echo "⚠ sandbox backend is configured but unreachable; React builds will fail"
    fi
    echo
    echo "✓ https://${HOST_IP}:${PORT}/"
    echo "  credentials: ${HOST}:/data/reify-deploy/.auth.env"
    echo "  sandbox:     ${HOST}:/data/reify-deploy/.sandbox.env"
    echo "  SSR apps:    https://${HOST_IP}:12889/apps/<project>/ (open 12889 in the firewall)"
    if [ "${REIFY_REMOVE_LEGACY:-1}" = "1" ]; then
      ssh "$HOST" "docker rm -f vibeforge-sandbox 2>/dev/null || true
docker network rm vibeforge-net 2>/dev/null || true" || true
    fi
    exit 0
  fi
  i=$((i + 1))
  /bin/sleep 1
done

echo "✗ health check failed; logs:"
ssh "$HOST" "docker logs --tail 80 ${NAME}-caddy" || true
ssh "$HOST" "docker logs --tail 40 ${NAME}" || true
exit 1
