# dotfiles

My personal development environment, managed with chezmoi. This is a public
backup of my configuration, not a supported setup for other users.

## Bootstrap targets and prerequisites

The bootstrap targets Ubuntu/Debian, including Ubuntu on WSL 2 and Raspberry Pi
OS. Android userland uses the existing lightweight profile. This is not a
general-purpose installer for arbitrary Linux distributions.

Start as the account that will own the dotfiles, with:

- `curl`, `git`, `sh`, `bash`, and working CA certificates;
- `apt-get` and sudo access;
- network access to GitHub, Homebrew, Python package indexes, and Node.js downloads;
- an interactive terminal for authentication and key passphrases.

On a minimal Ubuntu/Debian installation, install the download prerequisites first:

```sh
sudo apt-get update
sudo apt-get install -y curl git ca-certificates
```

Use a 64-bit OS on the Pi where possible. Homebrew's architecture support affects
installation time and availability; see its [Linux requirements](https://docs.brew.sh/Homebrew-on-Linux).

## Install

If this machine should use an existing GPG identity/password store, follow the
restore procedure below **before the first apply**. Otherwise, run:

```sh
sh -c "$(curl -fsLS https://get.chezmoi.io)" -- -b "$HOME/.local/bin" init --apply rvforest
```

This downloads chezmoi to `~/.local/bin`, clones the published repository, applies
configuration and external assets, then runs the ordered setup scripts. Local
commits must be pushed before this command can fetch them on another machine.

Setup installs the apt packages, Homebrew, declared Homebrew/uv tools, llm and
Nushell plugins, a default Node.js LTS runtime through fnm, and the repository's
secret-scanning hook. It then handles GitHub authentication, the Git signing key,
and GPG/pass initialization. Each script initializes its own PATH and XDG/GPG
environment; starting setup from bash is supported.

An existing working fnm default is preserved. A new Node default is installed
only if one is missing; Node major upgrades remain an explicit choice. Older nvm
installations are left on disk but are no longer loaded by this configuration.

## Pi coding agent

On non-mobile machines, setup installs Pi using its managed installer and a
separate Node runtime under `~/.local/share/dotfiles/pi-fnm`. Project Node
versions continue to use the normal fnm installation. The setup skips an
existing Pi installation it does not own. To update Pi, run `pi update`; to
update its Node runtime, change `node_version` in
`home/.chezmoiscripts/run_after_41-setup-pi.sh.tmpl` and apply again. Pi puts
its Node runtime on PATH for its own child commands as well, so commands it
runs may see that version instead of the project's fnm version.

Pi defaults to OpenRouter when no provider is already configured, and reads
`keys/openrouter/pi` from pass when needed. Restore the existing password store or
add the key with `pass insert keys/openrouter/pi`, then start `pi` and select a
model with `/model`. Existing Pi provider settings and custom credentials are
kept; the previous dotfiles-provided shared key command is migrated. The `llm`
command uses `keys/openrouter/llm`.

## Prompts during setup

Stay at the terminal to handle:

- sudo authentication and the Homebrew installer's confirmation;
- GitHub's browser/device authentication on a new machine (open the displayed URL
  on another device when connected over SSH);
- a passphrase for a newly generated Git signing key;
- the expiry and passphrase for a new GPG key, if no secret key was restored.

If an existing GitHub login cannot register a signing key, grant the required
scope and retry the apply:

```sh
gh auth refresh --hostname github.com --scopes admin:ssh_signing_key
```

Environment-provided GitHub tokens (for example in Codespaces) must also permit
personal signing-key management; otherwise use an appropriate personal login.
Signing-key uploads that fail are retried using the existing local key.

The default GPG expiry is 90 days. Renew expiring keys deliberately; bootstrap
does not extend their lifetime automatically. Creating a new key and empty
password store does not recover secrets encrypted for an old key.

## Restore an existing GPG identity and secrets

Initialize the checkout without applying it:

```sh
sh -c "$(curl -fsLS https://get.chezmoi.io)" -- -b "$HOME/.local/bin" init rvforest
```

If GPG is not installed yet, install it with `sudo apt-get install -y gnupg`.
Import your secret-key backup into the directory this configuration uses:

```sh
export GNUPGHOME="$HOME/.local/share/gnupg"
export PASSWORD_STORE_DIR="$HOME/.local/share/pass"
install -d -m 700 "$GNUPGHOME" "$PASSWORD_STORE_DIR"
gpg --import /secure/path/to/secret-key-backup.asc
gpg --list-secret-keys
```

Restore the encrypted password-store backup into `$PASSWORD_STORE_DIR`, including
its `.gpg-id` file and any existing Git configuration. The store's recipients must
match an imported decryption key. Keep the key backup outside this public repo.
Also restore owner trust if needed, after checking the imported key's fingerprint.

If an earlier setup created keys under `~/.gnupg`, inspect them with
`gpg --homedir "$HOME/.gnupg" --list-secret-keys` and explicitly export/import the
required identity into the configured directory. Bootstrap does not move or
delete an existing keyring.

Then apply:

```sh
~/.local/bin/chezmoi apply
```

For a new password store, add service credentials yourself. For example, the
`please` shell helper requires `pass insert keys/openrouter/llm`. Account credentials
and encrypted secret backups are not supplied by this repository.

## Finish the machine setup

These steps depend on the machine, account, or terminal client:

- **Login shell:** run `chsh -s "$(command -v zsh)"`, then reconnect or log in again.
  Use `exec zsh -l` to start it immediately in the current terminal. Codespaces,
  VS Code, or a WSL terminal profile may also need zsh selected in their settings.
- **Remote access:** install/configure the SSH server, authorized keys, Tailscale,
  and tailnet enrollment as appropriate. Bootstrap does not change SSH policy,
  firewall rules, or tailnet membership.
- **Terminal font:** select MesloLGS NF (or another suitable Nerd Font) in the
  terminal that renders the session. Installing fonts on the Pi/WSL filesystem
  does not configure the SSH client or Windows Terminal.
- **Editor/project setup:** let Neovim fetch its plugins and tools on first launch.
  Run `uv sync` explicitly for a Python project, open Neovim from the project
  directory, and select its environment once with `<leader>cv`. Later visits from
  that directory restore the selection; see the [Python editor notes](home/private_dot_config/nvim/README.md).
- **Optional services:** Homebrew's Docker packages provide client commands, not
  a configured Docker daemon. Configure a local engine or Docker Desktop/WSL
  integration if you intend to use them. Restore optional account state, such as
  Atuin sync credentials, separately.

## Resume and verify

After fixing an installation/authentication failure, rerun:

```sh
~/.local/bin/chezmoi apply
```

Managed tool failures return a nonzero status so chezmoi does not record the
failed setup script as complete. Successful earlier stages are retained.
Already installed tools are reused; the bootstrap is not transactional and does
not roll back earlier work when a later stage fails.

From a new zsh session, check the pieces you need:

```sh
command -v brew uv gh fnm node npm nu pre-commit nvim
gh auth status
node --version
npm --version
gpg --list-secret-keys
```

Verify that `pass show keys/openrouter/llm` decrypts successfully in a private terminal
if you use `please`; that command displays the secret. Check Git signing on the
first commit from the new machine.

`run_onchange` scripts run when their rendered contents change, not on a timer.
They are setup/reconciliation steps, not continuous health checks. Ordinary
bootstrap failures only need the normal retry command above.

The repository has isolated bootstrap/security regression tests and rendered
shell syntax checks. These do not replace a full first-install test on a clean
Linux/WSL machine.
