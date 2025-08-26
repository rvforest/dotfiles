# 60-aliases.zsh — aliases

# ls related
alias ls=eza
alias l='ls -lAh --no-user'
alias lt='eza --tree'

# uv tools - These inject the dependency into the existing environment.
# For example `jupyter` will start jupyter in the current venv even if it's not a dep
alias uvr='uv run'
alias ipython='uv run --with IPython ipython'
alias jupyter='uv run --with jupyter jupyter'

# zellij
alias zr='zellij run'
alias ze='zellij edit'

# Misc tools
alias bat=batcat
alias fd=fdfind
alias v=vim

# Git
alias wip='git stash --include-untracked > /dev/null && gcb "wip/$(git branch --show-current)" || gco "wip/$(git branch --show-current)" && git stash pop > /dev/null && gwip'
alias unwip='gunwip && gco "${$(git branch --show-current)#*wip/}" && git branch -D "wip/$(git branch --show-current)"'
