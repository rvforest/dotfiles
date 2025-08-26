# ohmyzsh.zsh - Oh My Zsh theme and plugin settings
export ZSH="$HOME/.oh-my-zsh"

plugins=(git zsh-syntax-highlighting)

zstyle ':omz:update' mode auto
zstyle ':omz:update' frequency 13

source $ZSH/oh-my-zsh.sh
