# Each chezmoi script runs in its own process; exports from an earlier script
# do not carry over. Use the same directories as the managed shell config.
export XDG_DATA_HOME={{ .xdg.data_home | quote }}
export XDG_CONFIG_HOME={{ .xdg.config_home | quote }}
export XDG_CACHE_HOME={{ .xdg.cache_home | quote }}
export XDG_STATE_HOME={{ .xdg.state_home | quote }}
export GNUPGHOME="$XDG_DATA_HOME/gnupg"
export PASSWORD_STORE_DIR="$XDG_DATA_HOME/pass"

{{ template "homebrew-env.sh" . }}
# uv puts tool executables here, including llm and pre-commit.
export PATH="$HOME/.local/bin:$PATH"
