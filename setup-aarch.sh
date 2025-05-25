set -euo pipefail

echo "apt update..."
sudo apt-get update -y

# git
echo "installing git..."
sudo apt install -y software-properties-common
sudo apt-add-repository -y ppa:git-core/ppa
sudo apt-get update
sudo apt-get install -y git

# neovim
echo "installing neovim..."
sudo apt install -y neovim

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

# gpg
echo "installing gpg..."
sudo apt-get install -y gpg

# eza
echo "installing eza..."
sudo apt-get install -y eza

# gh
echo "installing gh..."
(type -p wget >/dev/null || (sudo apt update && sudo apt-get install wget -y)) \
	&& sudo mkdir -p -m 755 /etc/apt/keyrings \
        && out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        && cat $out | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
	&& sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
	&& echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
	&& sudo apt update \
	&& sudo apt install gh -y


# delta
echo "installing delta..."
wget https://github.com/dandavison/delta/releases/download/0.18.2/delta-0.18.2-aarch64-apple-darwin.tar.gz
tar xvf delta-0.18.2-aarch64-apple-darwin.tar.gz
mv delta-0.18.2-aarch64-apple-darwin ~/.local/bin
rm -r delta-0.18.2-aarch64-apple-darwin.tar.gz 
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
