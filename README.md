# dotfiles

My personal dotfiles for configuring my development environment.

## Supported bootstrap targets

The one-command bootstrap is intended for Ubuntu/Debian targets.

## Prerequisites

Install these before running the bootstrap command:

- `curl`
- `sh` and `bash`
- a working Debian-family package manager (`apt-get`)
- `sudo` access for the user running setup
- outbound network access to GitHub and Homebrew downloads

You do **not** need to preinstall `git`, `gh`, `brew`, `uv`, `zsh`, or the rest of the managed tools. This repo installs them later in the bootstrap flow, so only the tools needed before that point are prerequisites.

## Bootstrap

Run:

```sh
sh -c "$(curl -fsLS https://get.chezmoi.io/lb)" -- init --apply rvforest
```

## What happens on the first run

1. chezmoi is downloaded and used to initialize this repo.
2. chezmoi fetches external assets managed by the repo.
3. chezmoi writes files into place.
4. chezmoi runs the setup scripts, which:
   - install system packages with `apt-get` (including `git`, `zsh`, and other base dependencies)
   - install Homebrew
   - install repo-managed CLI tools with Homebrew and `uv`
   - prompt for GitHub CLI authentication
   - create and upload the Git signing key

## Notes

- If the first run is interrupted, run the same command again.
