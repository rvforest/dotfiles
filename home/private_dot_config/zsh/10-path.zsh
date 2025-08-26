# 10-path.zsh — PATH and path-like variables

path_prepend() {
  for p in "$@"; do
    [[ -n $p && -d $p ]] || continue
    case ":${PATH}:" in *":${p}:"*) ;; *) PATH="${p}:${PATH}";; esac
  done
}

path_append() {
  for p in "$@"; do
    [[ -n $p && -d $p ]] || continue
    case ":${PATH}:" in *":${p}:"*) ;; *) PATH="${PATH}:${p}";; esac
  done
}

path_prepend "$HOME/bin" "$HOME/.local/bin" "/usr/local/bin"
path_append "/opt/nvim-linux-arm64/bin"
export PATH
