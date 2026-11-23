# Source after the P10k configuration. Reports the configured Tailscale SSH
# setting, not active sessions or whether tailnet policy permits a connection.
# Uses the same internal worker hooks as P10k's built-in asynchronous segments.
(( $+commands[tailscale] && $+commands[timeout] )) || return 0
(( ${+POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS} )) || return 0
zmodload zsh/datetime

typeset -g _ts_ssh_state='?'
typeset -gi _ts_ssh_generation=0
typeset -gF _ts_ssh_next_check=0 _ts_ssh_checked_at=0

function prompt_tailscale_ssh() {
  # Rendering only reads shell variables. Never wait for a subprocess here.
  local state=$_ts_ssh_state
  (( EPOCHREALTIME - _ts_ssh_checked_at <= 10 )) || state='?'
  case $state in
    on)  p10k segment -s ON      -f 214 -i $'\uf120' ;; # Terminal icon.
    off) return 0 ;; # Disabled: no segment.
    *)   p10k segment -s UNKNOWN -f 214 -i $'\uf128' ;; # Question mark.
  esac
}

function _p9k_prompt_tailscale_ssh_init() {
  _p9k__async_segments_compute+=_ts_ssh_schedule
}

function _ts_ssh_schedule() {
  emulate -L zsh
  (( EPOCHREALTIME >= _ts_ssh_next_check )) || return 0
  _ts_ssh_next_check=$((EPOCHREALTIME + 5))
  _p9k_worker_invoke tailscale_ssh "_ts_ssh_compute $_ts_ssh_generation"
}

function _ts_ssh_compute() {
  _p9k_worker_async "_ts_ssh_query $1" _ts_ssh_sync
}

function _ts_ssh_query() {
  emulate -L zsh
  local prefs state='?'
  local pattern='"RunSSH"[[:space:]]*:[[:space:]]*(true|false)'
  local MATCH
  local -a match mbegin mend

  # This runs in the worker. Failure/timeout means unknown, never disabled.
  if prefs=$(command timeout --kill-after=0.1s 1s tailscale debug prefs 2>/dev/null) &&
     [[ $prefs =~ $pattern ]]; then
    if [[ $match[1] == true ]]; then
      state=on
    else
      state=off
    fi
  fi
  # Send only the parsed state back, never the daemon's preferences output.
  print -r -- "_ts_ssh_accept $1 ${(q)state} $EPOCHREALTIME"
}

function _ts_ssh_sync() {
  _p9k_worker_reply "$REPLY"
}

function _ts_ssh_accept() {
  # Ignore any query that started before the most recent on/off command.
  (( $1 == _ts_ssh_generation )) || return 0
  _ts_ssh_state=$2
  _ts_ssh_checked_at=$3
  reset=2  # Ask P10k to rebuild and redraw the prompt with the new state.
}

function _ts_ssh_invalidate() {
  emulate -L zsh
  (( ++_ts_ssh_generation ))
  _ts_ssh_state='?'
  _ts_ssh_next_check=0
}

# Place it first on the right and keep re-sourcing this file idempotent.
typeset -ga POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS=(
  tailscale_ssh "${(@)POWERLEVEL9K_RIGHT_PROMPT_ELEMENTS:#tailscale_ssh}"
)

# No instant_prompt_tailscale_ssh: startup must not replay cached SSH status.
(( ! $+functions[p10k] )) || p10k reload
return 0
