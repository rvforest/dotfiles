# secrets.sh — pass-based secret loader for direnv
#
# Usage in .envrc:
#   load_secret ENV_VAR_NAME keys/your-secret-name
#
# To add a new secret:
#   pass insert keys/your-secret-name

load_secret() {
  local var="$1" key="$2" val
  if val="$(pass show "$key" 2>/dev/null)"; then
    if [[ -n $val ]]; then
      export "$var"="$val"
      return 0
    fi
  fi
  unset "$var"
  return 1
}
