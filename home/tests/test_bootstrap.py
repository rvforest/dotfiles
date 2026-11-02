"""Run rendered bootstrap scripts without the configured shell or real accounts.

Package managers, authentication, and key operations use temporary executables.
These checks do not install packages or replace a complete clean-VM bootstrap.
"""

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".chezmoiscripts"
CHEZMOI = shutil.which("chezmoi")


class Bootstrap:
    def __init__(self, root):
        self.root = root
        self.home = root / "home"
        self.brew_bin = self.home / ".linuxbrew/bin"
        self.local_bin = self.home / ".local/bin"
        self.brew_bin.mkdir(parents=True)
        self.local_bin.mkdir(parents=True)
        self.data = {"xdg": {key: str(root / directory) for key, directory in (
            ("data_home", "data"), ("config_home", "config"),
            ("state_home", "state"), ("cache_home", "cache"),
        )}}
        # No inherited Homebrew, local-bin, XDG, or keyring environment.
        self.env = {"HOME": str(self.home), "PATH": "/usr/bin:/bin",
                    "AUDIT_ROOT": str(root), "LANG": "C.UTF-8"}
        self.executable(self.brew_bin / "brew", (
            'test "$1" = shellenv || exit 99\n'
            f"printf '%s\\n' {shlex.quote('export PATH=' + shlex.quote(str(self.brew_bin)) + ':$PATH')}\n"
        ))

    def executable(self, path, body):
        path.write_text("#!/bin/bash\nset -eu\n" + body)
        path.chmod(0o700)

    def render(self, path):
        result = subprocess.run(
            [CHEZMOI, "--source", str(ROOT), "execute-template", "--override-data", json.dumps(self.data)],
            input=path.read_text(), capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stderr
        return result.stdout

    def run(self, name, expected_status=0):
        result = subprocess.run(
            ["/bin/bash"], input=self.render(SCRIPTS / name), env=self.env,
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == expected_status, result.stdout + result.stderr
        return result


@pytest.fixture
def bootstrap(tmp_path):
    assert CHEZMOI, "Requires chezmoi to render the actual scripts"
    return Bootstrap(tmp_path)


def test_later_scripts_find_tools_without_shell_startup(bootstrap):
    b = bootstrap
    module = b.root / "data/nushell/vendor/nupm/nupm.nu"
    module.parent.mkdir(parents=True)
    module.touch()
    b.data["nupm"] = {"git_repos": []}
    b.executable(b.brew_bin / "nu", 'exit 99\n')
    b.executable(b.brew_bin / "gh", 'printf "%s\\n" "$*" >> "$AUDIT_ROOT/gh-calls"\n')
    b.executable(b.local_bin / "pre-commit", (
        'printf "%s\\n" "$*" > "$AUDIT_ROOT/hook-call"\n'
        'printf "%s\\n" "$PWD" > "$AUDIT_ROOT/hook-repo"\n'
    ))
    b.run("run_onchange_after_32-install-nushell-deps.sh.tmpl")
    b.run("run_onchange_after_33-enable-secret-scanning.sh.tmpl")
    b.run("run_onchange_after_35-github-login.sh.tmpl")
    assert (b.root / "state/dotfiles/nupm-git-repos.txt").exists()
    assert (b.root / "hook-call").read_text().strip() == "install --install-hooks"
    assert Path((b.root / "hook-repo").read_text().strip()) == ROOT.parent
    assert (b.root / "gh-calls").read_text().splitlines() == [
        "auth status --hostname github.com", "auth setup-git",
    ]


def test_gpg_bootstrap_uses_the_shells_keyring_directory(bootstrap):
    b = bootstrap
    b.env["GNUPGHOME"] = str(b.home / ".gnupg")
    b.executable(b.brew_bin / "gpg", (
        'printf "%s\\n" "$GNUPGHOME" >> "$AUDIT_ROOT/gpg-homes"\n'
        'printf "sec   ed25519/FAKEKEY 2026-01-01 [SC]\\n"\n'
    ))
    b.executable(b.brew_bin / "pass", (
        'printf "%s\\n" "$PASSWORD_STORE_DIR" > "$AUDIT_ROOT/pass-home"\n'
        'touch "$PASSWORD_STORE_DIR/.gpg-id"\n'
    ))
    b.run("run_onchange_after_05-ensure-dirs.sh.tmpl")
    b.run("run_onchange_after_40-setup-gpg-and-pass.sh.tmpl")
    assert (b.root / "gpg-homes").read_text().splitlines() == [str(b.root / "data/gnupg")] * 2
    assert (b.root / "pass-home").read_text().strip() == str(b.root / "data/pass")
    assert (b.root / "data/gnupg").stat().st_mode & 0o777 == 0o700
    assert (b.root / "data/pass").stat().st_mode & 0o777 == 0o700
    assert (b.root / "cache/zsh").is_dir()
    assert not (b.home / ".gnupg").exists()


def test_failed_github_login_stops_before_git_setup(bootstrap):
    b = bootstrap
    b.executable(b.brew_bin / "gh", (
        'printf "%s\\n" "$*" >> "$AUDIT_ROOT/gh-calls"\n'
        'exit 7\n'
    ))
    b.run("run_onchange_after_35-github-login.sh.tmpl", expected_status=7)
    assert not any("setup-git" in line for line in (b.root / "gh-calls").read_text().splitlines())


@pytest.mark.parametrize("name", [
    "run_onchange_after_32-install-nushell-deps.sh.tmpl",
    "run_onchange_after_33-enable-secret-scanning.sh.tmpl",
])
def test_missing_dependency_does_not_mark_setup_successful(bootstrap, name):
    bootstrap.run(name, expected_status=1)


def test_first_shell_finds_homebrew_before_agent_setup(bootstrap):
    b = bootstrap
    script = b.render(ROOT / "private_dot_config/zsh/zshrc/10-path.zsh.tmpl")
    script += '\ncommand -v keychain\n'
    b.executable(b.brew_bin / "keychain", "exit 99\n")
    result = subprocess.run(
        [shutil.which("zsh"), "-f"], input=script, env=b.env,
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(b.brew_bin / "keychain")
