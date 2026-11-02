# Setup scripts and the first interactive shell must find an existing Homebrew
# installation even when the parent process has never loaded brew shellenv.
if ! command -v brew >/dev/null 2>&1; then
    for brew_prefix in "$HOME/.linuxbrew" /home/linuxbrew/.linuxbrew; do
        if [[ -x "$brew_prefix/bin/brew" ]]; then
            brew_env=$("$brew_prefix/bin/brew" shellenv)
            eval "$brew_env"
            break
        fi
    done
    unset brew_prefix brew_env
fi
