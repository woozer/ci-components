#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SETUP_IMAGE=ci-demo-setup:1
[ "$#" -gt 0 ] || set -- install

case "${1:-install}" in
  -h|--help|help)
    printf '%s\n' 'Usage: ./infra/setup.sh [install|check|status|verify|reset] [--accept-jcr-eula|--delete-data]' \
      'Requires Docker Desktop with Kubernetes enabled using the kind provisioner.' \
      'Installation state and credentials stay in ignored local directories.'
    exit 0 ;;
  install|check|status|verify|reset) ;;
  *) printf 'Unknown command: %s\n' "$1" >&2; exit 2 ;;
esac

command -v docker >/dev/null 2>&1 || { echo 'Docker Desktop is required.' >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo 'Start Docker Desktop first.' >&2; exit 1; }
docker inspect desktop-control-plane >/dev/null 2>&1 || {
  echo 'Enable Kubernetes in Docker Desktop and select the kind provisioner, then retry.' >&2
  exit 1
}
docker network inspect kind >/dev/null
docker build --quiet --tag "$SETUP_IMAGE" "$PROJECT_DIR/infra/setup" >/dev/null

exec docker run --rm --network kind --label org.ci-demo.role=installer \
  --mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
  --volume "$PROJECT_DIR:$PROJECT_DIR" --workdir "$PROJECT_DIR" \
  --env DEMO_ADMIN_HOST=host.docker.internal \
  "$SETUP_IMAGE" "$PROJECT_DIR/infra/setup/main.py" "$@"
