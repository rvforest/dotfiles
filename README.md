# dotfiles

My personal dotfiles for configuring my development environment.

## Supported bootstrap targets

The one-command bootstrap is intended for the Linux environments this repo already targets:

- WSL Ubuntu
- Ubuntu on Android userland
- Raspberry Pi OS
- GitHub Codespaces

Other systems may still work, but they are not the target for this setup path.

## Prerequisites

Install these before running the bootstrap command:

- `curl`
- `sh` and `bash`
- a working Debian-family package manager (`apt-get`)
- `sudo` access for the user running setup
- outbound network access to GitHub and Homebrew downloads

You do **not** need to preinstall `git`, `gh`, `brew`, `uv`, `zsh`, or the rest of the managed tools. This repo installs them later in the bootstrap flow, so only the tools needed before that point are prerequisites.

## Pre-run steps

1. Set the GitHub username that owns the dotfiles repo:

   ```sh
   export GITHUB_USERNAME=rvforest
   ```

2. Make sure the current shell can use `sudo` non-interactively enough to install packages when prompted.
3. Be ready to complete an interactive `gh auth login --web` step during the first apply.

## Bootstrap

Run:

```sh
sh -c "$(curl -fsLS https://get.chezmoi.io/lb)" -- init --apply "$GITHUB_USERNAME"
```

## What happens on the first run

The order matters:

1. chezmoi is downloaded and used to initialize this repo.
2. chezmoi fetches external assets managed by the repo.
3. chezmoi writes files into place.
4. chezmoi runs the setup scripts, which:
   - install system packages with `apt-get` (including `git`, `zsh`, and other base dependencies)
   - install Homebrew
   - install repo-managed CLI tools with Homebrew and `uv`
   - prompt for GitHub CLI authentication
   - create and upload the Git signing key

Because `git` and `gh` are installed later, they are intentionally not required before the bootstrap command runs.

## Notes

- If the first run is interrupted, run the same command again.
- On Android userland, use an Ubuntu-style environment that provides both `apt-get` and `sudo`.
