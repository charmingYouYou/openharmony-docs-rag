#!/usr/bin/env bash
# Install the OpenHarmony Docs RAG stack through Docker Compose using deploy/app.env.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_ENV_FILE="${ROOT_DIR}/deploy/app.env"

# Choose a Compose command that works on the current host.
resolve_compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    printf 'docker compose'
    return
  fi
  if command -v docker-compose >/dev/null 2>&1; then
    printf 'docker-compose'
    return
  fi
  printf '未找到 docker compose 或 docker-compose，请先安装 Docker Compose。\n' >&2
  exit 1
}

# Read a non-commented key from the deployment env file and fall back to the provided default.
read_env_value() {
  local key="$1"
  local fallback="$2"
  if [[ ! -f "${APP_ENV_FILE}" ]]; then
    printf '%s\n' "${fallback}"
    return
  fi
  local value
  value="$(grep -E "^${key}=" "${APP_ENV_FILE}" | tail -n 1 | cut -d '=' -f 2- || true)"
  if [[ -n "${value}" ]]; then
    printf '%s\n' "${value}"
    return
  fi
  printf '%s\n' "${fallback}"
}

# Wait until the deployed API reports healthy before returning control to the operator.
wait_for_api() {
  local api_port="$1"
  local health_url="http://127.0.0.1:${api_port}/health"

  for attempt in $(seq 1 60); do
    if command -v curl >/dev/null 2>&1; then
      if curl --silent --fail --max-time 5 "${health_url}" >/dev/null; then
        return
      fi
    else
      if docker exec openharmony-rag-app python -c "import urllib.request; urllib.request.urlopen('${health_url}', timeout=5).read()" >/dev/null 2>&1; then
        return
      fi
    fi
    sleep 2
  done

  printf '等待 API 健康检查超时：%s\n' "${health_url}" >&2
  exit 1
}

main() {
  local compose_cmd
  compose_cmd="$(resolve_compose_cmd)"

  if [[ ! -f "${APP_ENV_FILE}" ]]; then
    printf '未找到 %s，请先恢复仓库内置部署配置后再执行。\n' "${APP_ENV_FILE}" >&2
    exit 1
  fi

  local api_port
  api_port="$(read_env_value "API_PORT" "8000")"

  cd "${ROOT_DIR}"
  ${compose_cmd} --env-file "${APP_ENV_FILE}" pull
  ${compose_cmd} --env-file "${APP_ENV_FILE}" up -d
  wait_for_api "${api_port}"

  printf '\n部署完成。\n'
  printf 'Web / API 入口: http://localhost:%s\n' "${api_port}"
  printf '健康检查: http://localhost:%s/health\n' "${api_port}"
  printf '停止服务: %s --env-file %s down\n' "${compose_cmd}" "${APP_ENV_FILE}"
  printf '查看日志: %s --env-file %s logs -f app\n' "${compose_cmd}" "${APP_ENV_FILE}"
}

main "$@"
