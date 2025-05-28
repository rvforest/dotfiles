set -euo pipefail

echo "system..."
sudo apt-get update -y
sudo apt install -y build-essential
sudo apt install -y software-properties-common

# git
echo "installing git..."
sudo apt-add-repository -y ppa:git-core/ppa
sudo apt-get update
sudo apt-get install -y git

LAZYGIT_VERSION=$(curl -s "https://api.github.com/repos/jesseduffield/lazygit/releases/latest" | \grep -Po '"tag_name": *"v\K[^"]*')
curl -Lo lazygit.tar.gz "https://github.com/jesseduffield/lazygit/releases/download/v${LAZYGIT_VERSION}/lazygit_${LAZYGIT_VERSION}_Linux_x86_64.tar.gz"
tar xf lazygit.tar.gz lazygit
sudo install lazygit -D -t /usr/local/bin/

git config --global user.name 'Robert Forest'
git config --global user.email rvforest@gmail.com
git config --global core.editor vim
git config --global push.autoSetupRemote true
git config --global init.defaultBranch main
git config --global pull.rebase true

# neovim
echo "installing neovim..."
curl -LO https://github.com/neovim/neovim/releases/latest/download/nvim-linux-arm64.tar.gz
sudo rm -rf /opt/nvim
sudo tar -C /opt -xzf nvim-linux-arm64tar.gz
echo 'export PATH="$PATH:/opt/nvim-linux-arm64/bin"' >> ~/.zshrc

# zsh
echo "installing zsh..."
sudo apt-get install -y zsh

# omz
echo "installing omz..."
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" || true

# p10k
echo "installing p10k..."
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k" || true

# bat
echo "installing bat..."
sudo apt-get install -y bat

# fzf
echo "installing fzf..."
sudo apt-get install -y fzf

# fd
echo "installing fd..."
sudo apt-get install -y fd-find

# rg
echo "installing rg..."
sudo apt-get install -y ripgrep

# zsh-syntaxhighlighting
echo "installing zsh-syntax-highlighting..."
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting || true

# uv
echo "installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'eval "$(uv generate-shell-completion zsh)"' >> ~/.zshrc
echo 'eval "$(uvx --generate-shell-completion zsh)"' >> ~/.zshrc

# gpg
echo "installing gpg..."
sudo apt-get install -y gpg

# eza
echo "installing eza..."
sudo apt-get install -y eza

# gh
echo "installing gh..."
(type -p wget >/dev/null || (sudo apt update && sudo apt-get install wget -y)) &&
    sudo mkdir -p -m 755 /etc/apt/keyrings &&
    out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg &&
    cat $out | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null &&
    sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg &&
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null &&
    sudo apt update &&
    sudo apt install gh -y

# delta
echo "installing delta..."
wget https://github.com/dandavison/delta/releases/download/0.18.2/delta-0.18.2-aarch64-unknown-linux-gnu.tar.gz
tar xvf delta-0.18.2-aarch64-unknown-linux-gnu.tar.gz
mv delta-0.18.2-aarch64-unknown-linux-gnu/delta ~/.local/bin

git config --global core.pager delta
git config --global interactive.diffFilter 'delta --color-only'
git config --global delta.navigate true
git config --global merge.conflictStyle zdiff3

# you should use
git clone https://github.com/MichaelAquilina/zsh-you-should-use.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/you-should-use

# zellij
echo "installing zellij..."
wget https://github.com/zellij-org/zellij/releases/download/v0.42.2/zellij-aarch64-unknown-linux-musl.tar.gz
tar xvf zellij-aarch64-unknown-linux-musl.tar.gz
mv zellij ~/.local/bin
rm zellij-aarch64-unknown-linux-musl.tar.gz

# misc python tools
uv tool install tldr
uv tool install httpie

# sudo apt-get install -y

# git
git config --global user.email rvforest@gmail.com
git config --global user.name "Robert Forest"
