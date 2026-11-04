"""Run rendered bootstrap scripts without the configured shell or real accounts.

Package managers, authentication, and key operations use temporary executables.
These checks do not install packages or replace a complete clean-VM bootstrap.
"""

import json
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
        # Keep a missing fixture installation from falling through to the
        # developer machine's system-wide Homebrew installation.
        return result.stdout.replace("/home/linuxbrew/.linuxbrew", str(self.root / "global-linuxbrew"))

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
    module = b.root / "data/nushell/vendor/nupm/nupm/mod.nu"
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
        "auth status --hostname github.com",
    ]
    config = b.root / "managed-git-config"
    config.write_text(b.render(ROOT / "private_dot_config/private_git/config.tmpl"))
    helper = subprocess.run(
        ["git", "config", "--file", str(config), "--get-all", "credential.https://github.com.helper"],
        env=b.env, capture_output=True, text=True, timeout=15,
    )
    assert helper.returncode == 0, helper.stderr
    assert helper.stdout.splitlines() == ["", "!gh auth git-credential"]


def test_failed_homebrew_download_does_not_complete_the_stage(bootstrap):
    b = bootstrap
    (b.brew_bin / "brew").unlink()
    b.executable(b.local_bin / "curl", "exit 7\n")
    result = b.run("run_onchange_after_25-install-homebrew.sh.tmpl", expected_status=7)
    assert "Homebrew installation completed" not in result.stdout


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


def test_failed_github_login_does_not_complete_the_stage(bootstrap):
    b = bootstrap
    b.executable(b.brew_bin / "gh", (
        'printf "%s\\n" "$*" >> "$AUDIT_ROOT/gh-calls"\n'
        'exit 7\n'
    ))
    b.run("run_onchange_after_35-github-login.sh.tmpl", expected_status=7)
    calls = (b.root / "gh-calls").read_text().splitlines()
    assert calls[0] == "auth status --hostname github.com"
    assert calls[1].startswith("auth login ")
    assert len(calls) == 2


@pytest.mark.parametrize("initial_config", ["", "# en_US.UTF-8 UTF-8\n", "en_US.UTF-8 UTF-8\n"])
def test_locale_generation_does_not_require_an_existing_locale(bootstrap, initial_config):
    b = bootstrap
    locale_gen = b.root / "locale.gen"
    locale_gen.write_text(initial_config)
    b.executable(b.brew_bin / "locale", '''
printf 'C.utf8\n'
if [[ -f "$AUDIT_ROOT/generated-locale" ]]; then printf 'en_US.utf8\n'; fi
''')
    for command in ("locale-gen", "update-locale"):
        b.executable(b.brew_bin / command, "exit 99\n")
    b.executable(b.brew_bin / "sudo", '''
printf '%s\n' "$*" >> "$AUDIT_ROOT/locale-calls"
case "$1" in
    sh) "$@" ;;
    locale-gen)
        grep -Eq '^en_US.UTF-8 UTF-8$' "$AUDIT_ROOT/locale.gen"
        touch "$AUDIT_ROOT/generated-locale" ;;
esac
''')
    # Redirect only the system configuration path; the rendered script and
    # its privileged append otherwise run unchanged in this temporary tree.
    script = b.render(SCRIPTS / "run_onchange_after_15-setup-locale.sh.tmpl").replace(
        "/etc/locale.gen", str(locale_gen),
    )
    result = subprocess.run(["/bin/bash"], input=script, env=b.env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    calls = (b.root / "locale-calls").read_text().splitlines()
    assert "locale-gen en_US.UTF-8" in calls
    assert "update-locale LANG=en_US.UTF-8" in calls
    assert locale_gen.read_text().splitlines().count("en_US.UTF-8 UTF-8") == 1
    result = subprocess.run(["/bin/bash"], input=script, env=b.env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (b.root / "locale-calls").read_text().splitlines() == calls


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


@pytest.mark.parametrize("existing_default", [False, True])
def test_node_setup_installs_lts_only_when_no_default_exists(bootstrap, existing_default):
    b = bootstrap
    b.executable(b.brew_bin / "fnm", '''
printf '%s\n' "$*" >> "$AUDIT_ROOT/fnm-calls"
case "$*" in
    'env --shell bash') printf '%s\n' 'export FNM_MULTISHELL_PATH="$AUDIT_ROOT/node"' ;;
    'use default') test -f "$AUDIT_ROOT/default-node" ;;
    'install --lts --use') touch "$AUDIT_ROOT/default-node" ;;
    current) printf 'v24.0.0\n' ;;
    'default v24.0.0') test -f "$AUDIT_ROOT/default-node" ;;
    *) exit 99 ;;
esac
''')
    for command in ("node", "npm"):
        b.executable(b.brew_bin / command, 'test -f "$AUDIT_ROOT/default-node"\nprintf "available\\n"\n')
    if existing_default:
        (b.root / "default-node").touch()
    for attempt in range(2):
        b.run("run_onchange_after_31-setup-node.sh.tmpl")
        calls = (b.root / "fnm-calls").read_text().splitlines()
        assert calls.count("install --lts --use") == (0 if existing_default else 1)


def test_node_download_failure_is_not_reported_as_success(bootstrap):
    b = bootstrap
    b.executable(b.brew_bin / "fnm", '''
case "$1" in
    env) printf '%s\n' 'export FNM_MULTISHELL_PATH="$AUDIT_ROOT/node"' ;;
    use) exit 1 ;;
    install) exit 7 ;;
    *) exit 99 ;;
esac
''')
    b.run("run_onchange_after_31-setup-node.sh.tmpl", expected_status=7)


@pytest.mark.parametrize("is_mobile", [False, True])
def test_npm_packages_use_default_runtime_and_install_only_when_missing(bootstrap, is_mobile):
    b = bootstrap
    b.data.update({"is_mobile": is_mobile, "npm": {"packages": {
        "core": ["@softov/ahpc"], "desktop": ["desktop-cli"],
    }}})
    b.executable(b.brew_bin / "fnm", '''
case "$*" in
    'env --shell bash') printf '%s\n' 'export DEFAULT_NODE_ACTIVE=1' ;;
    'use default') ;;
    *) exit 99 ;;
esac
''')
    b.executable(b.brew_bin / "node", "exit 0\n")
    b.executable(b.brew_bin / "npm", '''
test "$DEFAULT_NODE_ACTIVE" = 1
case "$1" in
    --version) ;;
    list) grep -Fxq -- "$4" "$AUDIT_ROOT/npm-installed" ;;
    install)
        printf '%s\n' "$3" >> "$AUDIT_ROOT/npm-installed" ;;
    *) exit 99 ;;
esac
''')
    (b.root / "npm-installed").touch()
    for attempt in range(2):
        b.run("run_onchange_after_31-setup-node.sh.tmpl")
    assert (b.root / "npm-installed").read_text().splitlines() == (
        ["@softov/ahpc"] if is_mobile else ["@softov/ahpc", "desktop-cli"]
    )


def test_real_fnm_reuses_an_existing_runtime_without_downloading(bootstrap):
    fnm = shutil.which("fnm")
    if not fnm:
        pytest.skip("Requires fnm for the existing-runtime integration check")
    b = bootstrap
    (b.brew_bin / "fnm").symlink_to(fnm)
    runtime = b.root / "runtime"
    runtime.mkdir()
    b.env.update(FNM_DIR=str(b.root / "data/fnm"), XDG_RUNTIME_DIR=str(runtime))
    node_bin = b.root / "data/fnm/node-versions/v24.0.0/installation/bin"
    node_bin.mkdir(parents=True)
    b.executable(node_bin / "node", 'printf "v24.0.0\\n"\n')
    b.executable(node_bin / "npm", 'printf "11.0.0\\n"\n')
    result = subprocess.run(
        [fnm, "default", "v24.0.0"], env=b.env, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    result = b.run("run_onchange_after_31-setup-node.sh.tmpl")
    assert "v24.0.0" in result.stdout
    assert "11.0.0" in result.stdout


def test_normal_apply_retries_failed_tool_setup_and_remembers_success(bootstrap):
    b = bootstrap
    b.data.update({
        "is_mobile": False,
        "homebrew": {"formulas": {"core": ["audit-tool"], "desktop": []}, "casks": {"desktop": []}},
        "uv": {"tools": {"core": [], "desktop": []}}, "llm": {"plugins": []},
    })
    shellenv = 'export PATH=' + shlex.quote(str(b.brew_bin)) + ':$PATH'
    b.executable(b.brew_bin / "brew", (
        f'if [[ "$1" == shellenv ]]; then printf "%s\\n" {shlex.quote(shellenv)}; exit; fi\n'
        '''
printf '%s\n' "$*" >> "$AUDIT_ROOT/brew-calls"
case "$1" in
    list)
        if [[ "$2" == --formula && -f "$AUDIT_ROOT/installed-tool" ]]; then printf 'audit-tool\n'; fi ;;
    outdated) ;;
    install)
        if [[ -f "$AUDIT_ROOT/fail-install" ]]; then exit 7; fi
        touch "$AUDIT_ROOT/installed-tool" ;;
    *) exit 99 ;;
esac
'''
    ))
    b.executable(b.brew_bin / "uv", '[[ "$1 $2" == "tool list" ]]\n')
    source = b.root / "source/.chezmoiscripts"
    source.mkdir(parents=True)
    (source / "run_onchange_after_30-install-tools.sh").write_text(
        b.render(SCRIPTS / "run_onchange_after_30-install-tools.sh.tmpl")
    )
    config = b.root / "chezmoi.json"
    config.write_text("{}")
    args = [CHEZMOI, "--config", str(config), "--source", str(source.parent),
            "--destination", str(b.home), "--persistent-state", str(b.root / "chezmoi-state.boltdb"),
            "--cache", str(b.root / "cache"), "apply"]
    failure = b.root / "fail-install"
    failure.touch()
    first = subprocess.run(args, env=b.env, capture_output=True, text=True, timeout=30)
    assert first.returncode != 0, first.stdout + first.stderr
    assert "Tool setup incomplete" in first.stderr
    failure.unlink()
    for attempt in range(2):
        result = subprocess.run(args, env=b.env, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
    # First apply failed, second retried, third skipped the successful script.
    calls = (b.root / "brew-calls").read_text().splitlines()
    assert calls.count("install --formula audit-tool") == 2


@pytest.mark.parametrize("already_registered", [False, True])
def test_signing_registration_retries_without_recreating_the_key(bootstrap, already_registered):
    b = bootstrap
    b.executable(b.brew_bin / "ssh-keygen", '''
printf 'generate\n' >> "$AUDIT_ROOT/key-generations"
while [[ "$1" != -f ]]; do shift; done
printf 'fixture-private-key\n' > "$2"
printf 'ssh-ed25519 AUDITPUBLICKEY fixture\n' > "$2.pub"
''')
    b.executable(b.brew_bin / "gh", '''
printf '%s\n' "$*" >> "$AUDIT_ROOT/gh-calls"
case "$1" in
    api)
        if [[ -f "$AUDIT_ROOT/registered-key" ]]; then
            printf 'ssh-ed25519 AUDITPUBLICKEY fixture\n'
        fi ;;
    ssh-key)
        if [[ -f "$AUDIT_ROOT/fail-upload" ]]; then exit 7; fi
        touch "$AUDIT_ROOT/registered-key" ;;
    *) exit 99 ;;
esac
''')
    if already_registered:
        (b.root / "registered-key").touch()
    else:
        failure = b.root / "fail-upload"
        failure.touch()
        b.run("run_after_40-setup-git-signing-keys.sh.tmpl", expected_status=7)
        assert not (b.root / "state/dotfiles/git-signing-key.pub").exists()
        failure.unlink()
    b.run("run_after_40-setup-git-signing-keys.sh.tmpl")
    calls = (b.root / "gh-calls").read_text()
    b.run("run_after_40-setup-git-signing-keys.sh.tmpl")
    assert (b.root / "gh-calls").read_text() == calls
    assert calls.count("ssh-key add") == (0 if already_registered else 2)
    assert (b.root / "key-generations").read_text() == "generate\n"
    assert (b.root / "state/dotfiles/git-signing-key.pub").read_text() == "ssh-ed25519 AUDITPUBLICKEY\n"
    assert 'namespaces="git" ssh-ed25519 AUDITPUBLICKEY' in (b.root / "config/git/allowed_signers").read_text()
