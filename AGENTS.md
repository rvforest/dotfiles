# Repository Guide

## Overview

This repository is a chezmoi-managed dotfiles repo. The `home/` tree mirrors the target home directory using chezmoi naming conventions such as `dot_`, `private_`, and `.tmpl`. Changes here usually affect shell startup, editor behavior, git configuration, external assets, or bootstrap scripts.

## Main Surfaces

- `home/.chezmoi.toml.tmpl` defines shared template data and machine-classification flags.
- `home/.chezmoidata/*.yaml` stores declarative package and tool data used by setup scripts.
- `home/.chezmoiscripts/` contains ordered setup steps; numeric prefixes imply intended execution order.
- `home/.chezmoiexternal.toml.tmpl` manages downloaded external assets such as oh-my-zsh, powerlevel10k, nupm, fonts, and standalone binaries.
- `home/private_dot_zshrc` and `home/private_dot_config/zsh/zshrc/*.zsh.tmpl` define a modular zsh configuration loaded in lexical order.
- `home/private_dot_config/` contains app configs for tools such as git, nvim, zellij, atuin, gh, and direnv.
- `scripts/` is not the main chezmoi application path; `setup-aarch.sh` is legacy, but do not assume every file in `scripts/` is unused.

## Target Environments

- Primary Linux targets are WSL Ubuntu, Ubuntu on Android userland, Raspberry Pi OS, and GitHub Codespaces.
- The Android userland environment is treated as mobile and should stay relatively lightweight.
- WSL-specific behavior already exists in the repo and should be preserved when relevant.
- Avoid adding broad portability work beyond these environments unless the user asks for it.

## Repo Conventions

- Treat `.tmpl` files as Go templates rendered by chezmoi.
- Prefer editing the owning declarative data file when behavior is already data-driven.
- Keep setup scripts idempotent and cheap on repeat runs.
- Prefer existing machine flags over introducing new host-detection logic.
- Do not add or remove tools or dependencies without a concrete reason.
- Preserve the existing split-config style instead of collapsing modular files into monoliths.

## Machine Flags

The main derived flags live in `home/.chezmoi.toml.tmpl`:

- `is_mobile`
- `is_ephemeral`
- `is_headless`
- `is_wsl`

Use these flags when a change needs host-specific behavior.

## Common Change Routes

- For package/bootstrap changes, start with `home/.chezmoidata/*.yaml` and the corresponding script in `home/.chezmoiscripts/`.
- For downloaded tools, themes, fonts, or vendored repos, start with `home/.chezmoiexternal.toml.tmpl`.
- For shell behavior, check `home/private_dot_zshrc` and then the relevant file under `home/private_dot_config/zsh/zshrc/`.
- For git behavior, start with `home/private_dot_config/private_git/config.tmpl` and any related key-signing script.
- For editor behavior, check `home/private_dot_config/nvim/`.

## Validation Workflow

- For bash templates, validate rendered output with `chezmoi execute-template < path/to/script.tmpl | bash -n`.
- For plain bash scripts, use `bash -n`.
- For zsh fragments, prefer validating through their owning loader or a focused shell parse when practical.
- Editor diagnostics on shell `.tmpl` files may report false positives on Go-template delimiters; trust rendered-script validation over raw template parsing.
- When changing declarative data, validate the immediate owning script rather than doing only diff review.

## State and Ownership

- Repo-owned setup state is tracked under `${XDG_STATE_HOME:-$HOME/.local/state}/dotfiles`.
- Some managed source checkouts live under `${XDG_DATA_HOME:-$HOME/.local/share}/dotfiles`.
- Reconcile only repo-owned items when possible instead of trying to fully manage everything on the machine.

## Editing Guidance

- Keep changes local to the owning abstraction.
- If behavior is currently duplicated between data and script, prefer consolidating around the declarative source of truth.
- Add comments when an abstraction or host-specific branch would otherwise be unclear to a new maintainer.
- Do not assume files outside the current change area are dead code without checking usage first.
