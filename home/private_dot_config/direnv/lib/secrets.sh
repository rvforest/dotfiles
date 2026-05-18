# secrets.sh — pass-based secret loader for direnv
#
# Usage in .envrc:
#   export ENV_VAR_NAME="$(load_secret keys/your-secret-name)"
#   load_secret keys/your-secret-name ENV_VAR_NAME
#
#
# To add a new secret:
#   pass insert keys/your-secret-name

load_secret() {
  local key="$1" var="$2" val
  if val="$(pass show "$key" 2>/dev/null)"; then
    if [[ -n $val ]]; then
      if [[ -n $var ]]; then
        export "$var"="$val"
      else
        echo "$val"
      fi
      return 0
    fi
  fi
  unset "$var"
  return 1
}
