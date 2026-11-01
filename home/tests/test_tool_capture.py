"""Isolated capture/reconciliation checks: pytest -q tests.

Requires the existing chezmoi, yq (Mike Farah), jq, bash, and zsh commands.
All package-manager calls use fakes; manifests and state live in a temporary tree.
"""

import json
import os
from pathlib import Path
import pty
import select
import shlex
import shutil
import subprocess
import sys
import time

import pytest


ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "dot_local/bin/executable_dotfiles-tool-capture.tmpl"
INSTALLER = ROOT / ".chezmoiscripts/run_onchange_after_30-install-tools.sh.tmpl"
FUNCTIONS = ROOT / "private_dot_config/zsh/zshrc/70-functions.zsh.tmpl"

FAKE_MANAGER = r'''
import json
import os
from pathlib import Path
import sys

root = Path(os.environ["CAPTURE_TEST_ROOT"])
manager = Path(sys.argv[0]).name
args = sys.argv[1:]
with (root / "commands.jsonl").open("a") as stream:
    stream.write(json.dumps([manager, *args]) + "\n")
state = json.loads((root / "installed.json").read_text())
if [manager, *args] in state.get("failed_commands", []):
    sys.exit("Simulated package-manager failure")
if os.environ.get("CAPTURE_TEST_EXIT"):
    sys.exit(int(os.environ["CAPTURE_TEST_EXIT"]))
if manager == "brew":
    if args == ["--cellar"]:
        print(root / "cellar")
    elif args == ["--caskroom"]:
        print(root / "caskroom")
    elif args and args[0] == "list":
        for name in state["casks" if "--cask" in args else "formulas"]:
            print(name)
    elif args and args[0] == "outdated":
        for name in state.get("outdated_brew", []):
            print(name)
    elif not any(arg in args for arg in ("install", "upgrade", "uninstall")):
        sys.exit("Unexpected brew call: " + repr(args))
elif manager == "uv":
    if args == ["tool", "dir"]:
        print(root / "uv-tools")
    elif args[:2] == ["tool", "list"]:
        for name in state.get("outdated_uv", []) if "--outdated" in args else state["uv"]:
            print(name + " v1.0.0")
    elif not any(arg in args for arg in ("install", "upgrade", "uninstall")):
        sys.exit("Unexpected uv call: " + repr(args))
'''


@pytest.fixture(scope="session", autouse=True)
def required_commands():
    for dependency in ("chezmoi", "yq", "jq", "bash", "zsh"):
        if not shutil.which(dependency):
            pytest.fail(f"Missing test dependency: {dependency}")


class TestToolCapture:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.source = self.root / "source"
        (self.source / ".chezmoidata").mkdir(parents=True)
        self.manifest = self.source / ".chezmoidata/system_tools.yaml"
        shutil.copyfile(ROOT / ".chezmoidata/system_tools.yaml", self.manifest)
        self.state = self.root / "state/dotfiles"
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "DOTFILES_TOOLS_SOURCE_HOME": str(self.source),
            "XDG_STATE_HOME": str(self.root / "state"),
            "XDG_DATA_HOME": str(self.root / "data"),
            "XDG_CONFIG_HOME": str(self.root / "config"),
            "XDG_CACHE_HOME": str(self.root / "cache"),
            "CAPTURE_TEST_ROOT": str(self.root),
        }
        for key in ("CAPTURE_TEST_EXIT",):
            self.env.pop(key, None)
        for manager in ("brew", "uv"):
            self.executable(self.bin / manager, f"#!{sys.executable}\n" + FAKE_MANAGER)
        # Even an unexpected bootstrap call must never download or install anything.
        self.executable(self.bin / "curl", "#!/bin/sh\nexit 99\n")
        self.executable(self.bin / "llm", "#!/bin/sh\nexit 99\n")
        nvm = self.root / "data/nvm/nvm.sh"
        nvm.parent.mkdir(parents=True)
        nvm.write_text("# Bootstrap is intentionally disabled in this fixture.\n")
        # Treat the repo's existing baseline as installed. Only the fixture's
        # new tools need simulated installs during reconciliation.
        self.installed = {
            "formulas": self.values(".homebrew.formulas.core + .homebrew.formulas.desktop"),
            "casks": [],
            "uv": self.values(".uv.tools.core"),
        }
        self.save_installed()
        self.capture_script = self.bin / "dotfiles-tool-capture"
        self.render(CAPTURE, self.capture_script)

    def executable(self, path, content):
        path.write_text(content)
        path.chmod(0o700)

    def run_command(self, args, **kwargs):
        result = subprocess.run(
            args, env=self.env, text=True, capture_output=True, timeout=60,
            **kwargs,
        )
        assert result.returncode == 0, f"{args!r}\n{result.stdout}\n{result.stderr}"
        return result

    def render(self, template, target, mobile=False, manifest=False):
        data = {"is_mobile": mobile}
        if manifest:
            data.update(json.loads(self.run_command([
                "yq", "-o=json", ".", str(self.manifest),
            ]).stdout))
        result = self.run_command([
            "chezmoi", "execute-template", "--override-data", json.dumps(data),
        ], input=template.read_text())
        self.executable(target, result.stdout)

    def save_installed(self):
        (self.root / "installed.json").write_text(json.dumps(self.installed))

    def commands(self):
        path = self.root / "commands.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def clear_commands(self):
        (self.root / "commands.jsonl").write_text("")

    def values(self, expression):
        return json.loads(self.run_command([
            "yq", "-o=json", expression, str(self.manifest),
        ]).stdout)

    def formula(self, name, *, requested=True, tap="homebrew/core", aliases=()):
        receipt = self.root / f"cellar/{name}/1.0/INSTALL_RECEIPT.json"
        receipt.parent.mkdir(parents=True)
        receipt.write_text(json.dumps({
            "installed_on_request": requested,
            "source": {"tap": tap}, "aliases": list(aliases),
        }))

    def uv_receipt(self, name, requirement, options=""):
        receipt = self.root / f"uv-tools/{name}/uv-receipt.toml"
        receipt.parent.mkdir(parents=True)
        receipt.write_text(f"[tool]\nrequirements = [{requirement}]\n{options}")

    def capture(self, manager, answers=""):
        return self.run_command([str(self.capture_script), manager], input=answers)

    def reconcile(self, mobile=False):
        script = self.root / "installer.sh"
        self.render(INSTALLER, script, mobile=mobile, manifest=True)
        return self.run_command(["bash", str(script)])

    def test_brew_scopes_dependencies_aliases_and_repeat(self):
        self.formula("capture-core")
        self.formula("capture-desktop", tap="example/tools")
        self.formula("capture-dependency", requested=False)
        self.formula("capture-alias", aliases=["ripgrep"])
        cask = self.root / "caskroom/capture-app"
        cask.mkdir(parents=True)
        self.capture("brew", "c\nd\nd\n")
        assert "capture-core" in self.values(".homebrew.formulas.core")
        assert "example/tools/capture-desktop" in self.values(".homebrew.formulas.desktop")
        assert self.values(".homebrew.casks.desktop") == ["capture-app"]
        assert "capture-dependency" not in self.manifest.read_text()
        assert "capture-alias" not in self.manifest.read_text()
        assert "capture-core" in (self.state / "homebrew-formulas.txt").read_text()
        assert "capture-app" in (self.state / "homebrew-casks.txt").read_text()
        before = self.manifest.read_text()
        assert "not managed" not in self.capture("brew").stdout
        assert self.manifest.read_text() == before

    def test_local_choices_are_remembered(self):
        self.formula("capture-local")
        (self.root / "caskroom/capture-local-app").mkdir(parents=True)
        self.uv_receipt("capture-local-uv", '{ name = "capture-local-uv" }')
        before = self.manifest.read_text()
        self.capture("brew", "l\nl\n")
        self.capture("uv", "l\n")
        for manager in ("brew", "uv"):
            assert "not managed" not in self.capture(manager).stdout
        assert self.manifest.read_text() == before
        assert (self.state / "unmanaged-uv-tools.txt").read_text() == "capture-local-uv\n"

    def test_uv_requirements_round_trip_and_reconcile(self):
        expected = [
            "capture-extra[cli]>=1.2,<2",
            "capture-git @ git+https://example.invalid/tools.git@abc123#subdirectory=cli",
            "capture-old==2.0",
            'capture-url @ https://example.invalid/pkg.whl ; python_version >= "3.11"',
        ]
        self.uv_receipt("capture-extra", '{ name = "capture-extra", extras = ["cli"], specifier = ">=1.2,<2" }')
        self.uv_receipt("capture-git", '{ name = "capture-git", git = "https://example.invalid/tools.git?branch=main&subdirectory=cli#abc123" }')
        self.uv_receipt("capture-old", '"capture-old==2.0"')
        self.uv_receipt("capture-url", '{ name = "capture-url", url = "https://example.invalid/pkg.whl", marker = \'python_version >= "3.11"\' }')
        self.capture("uv", "d\nd\nd\nd\n")
        assert self.values(".uv.tools.desktop") == expected
        assert (self.state / "uv-tools.txt").read_text().splitlines() == expected
        before = self.manifest.read_text()
        assert "not managed" not in self.capture("uv").stdout
        assert self.manifest.read_text() == before
        self.clear_commands()
        self.reconcile()
        for requirement in expected:
            assert ["uv", "tool", "install", requirement] in self.commands()

    def test_uv_install_options_remain_unmanaged(self):
        self.uv_receipt("capture-python", '{ name = "capture-python" }', 'python = "3.12"\n')
        self.uv_receipt("capture-with", '{ name = "capture-with" }, { name = "extra" }')
        self.uv_receipt("capture-index", '{ name = "capture-index", index = "https://example.invalid/simple" }')
        self.uv_receipt("capture-constraints", '{ name = "capture-constraints" }', 'constraints = [{ name = "extra", specifier = "<2" }]\n')
        self.uv_receipt("capture-options", '{ name = "capture-options" }', '[tool.options]\nindex-url = "https://example.invalid/simple"\n')
        self.uv_receipt("capture-editable", '{ name = "capture-editable", editable = true }')
        before = self.manifest.read_text()
        result = self.capture("uv", "d\n" * 6)
        assert result.stderr.count("leaving it unmanaged") == 6
        assert "not managed" not in result.stdout
        assert self.manifest.read_text() == before

    def test_eof_and_invalid_answers_leave_manifest_unchanged(self):
        self.formula("capture-deferred")
        before = self.manifest.read_text()
        for answers in ("", "unexpected\n"):
            assert "Left capture-deferred unmanaged" in self.capture("brew", answers).stdout
            assert self.manifest.read_text() == before
        assert "not managed" in self.capture("brew").stdout

    def test_mobile_default_and_reconciliation_scope(self):
        self.uv_receipt("capture-core", '{ name = "capture-core" }')
        self.uv_receipt("capture-desktop", '{ name = "capture-desktop" }')
        self.render(CAPTURE, self.capture_script, mobile=True)
        self.capture("uv", "\nd\n")
        assert "capture-core" in self.values(".uv.tools.core")
        assert "capture-desktop" in self.values(".uv.tools.desktop")
        self.reconcile(mobile=True)
        assert ["uv", "tool", "install", "capture-core"] in self.commands()
        assert ["uv", "tool", "install", "capture-desktop"] not in self.commands()
        assert ["brew", "install", "--formula", "docker"] not in self.commands()

    def test_reconcile_changed_requirements_removed_tools_and_tapped_formula(self):
        self.uv_receipt("capture-version", '{ name = "capture-version", specifier = "==2" }')
        self.formula("capture-tapped", tap="example/tools")
        self.capture("uv", "d\n")
        self.capture("brew", "d\n")
        (self.state / "uv-tools.txt").write_text("capture-version==1\ncapture-removed\n")
        self.installed["uv"] += ["capture-version", "capture-removed"]
        self.installed["formulas"] += ["example/tools/capture-tapped"]
        self.save_installed()
        self.clear_commands()
        self.reconcile()
        assert ["uv", "tool", "install", "--force", "capture-version==2"] in self.commands()
        assert ["uv", "tool", "uninstall", "capture-removed"] in self.commands()
        assert ["brew", "install", "--formula", "example/tools/capture-tapped"] not in self.commands()

    @pytest.mark.parametrize("previous_spec", [None, "capture-version==1"])
    @pytest.mark.parametrize("already_installed", [False, True])
    def test_failed_uv_requirement_update_is_retried(self, previous_spec, already_installed):
        self.run_command([
            "yq", "-i", '.uv.tools.desktop = ["capture-version==2"]', str(self.manifest),
        ])
        self.state.mkdir(parents=True)
        managed = self.state / "uv-tools.txt"
        managed.write_text(previous_spec + "\n" if previous_spec else "")
        if already_installed:
            self.installed["uv"].append("capture-version")
        update = ["uv", "tool", "install"]
        if already_installed:
            update.append("--force")
        update.append("capture-version==2")
        self.installed["failed_commands"] = [update]
        self.save_installed()

        result = self.reconcile()
        assert update in self.commands()
        assert "Failed to " in result.stderr
        assert "capture-version==2" not in managed.read_text().splitlines()
        if previous_spec:
            assert previous_spec in managed.read_text().splitlines()

        self.installed["failed_commands"] = []
        self.save_installed()
        self.clear_commands()
        self.reconcile()
        assert update in self.commands()
        assert "capture-version==2" in managed.read_text().splitlines()
        if not already_installed:
            self.installed["uv"].append("capture-version")
            self.save_installed()
        self.clear_commands()
        self.reconcile()
        assert update not in self.commands()

    def test_failed_uv_uninstall_is_retried(self):
        self.state.mkdir(parents=True)
        managed = self.state / "uv-tools.txt"
        managed.write_text("capture-removed==1\n")
        self.installed["uv"].append("capture-removed")
        uninstall = ["uv", "tool", "uninstall", "capture-removed"]
        self.installed["failed_commands"] = [uninstall]
        self.save_installed()
        self.reconcile()
        assert uninstall in self.commands()
        assert "capture-removed==1" in managed.read_text().splitlines()

        self.installed["failed_commands"] = []
        self.save_installed()
        self.clear_commands()
        self.reconcile()
        assert uninstall in self.commands()
        assert "capture-removed==1" not in managed.read_text().splitlines()

    @pytest.mark.parametrize(("desired", "installed", "previous", "install", "uninstall"), [
        ("new/tap/capture-tool", "old/tap/capture-tool", "old/tap/capture-tool", True, True),
        ("new/tap/capture-tool", "capture-tool", None, True, False),
        ("new/tap/capture-tool", "new/tap/capture-tool", "capture-tool", False, False),
        ("capture-tool", "new/tap/capture-tool", "new/tap/capture-tool", False, False),
        ("homebrew/core/capture-tool", "capture-tool", "capture-tool", False, False),
        ("homebrew/core/capture-tool", "new/tap/capture-tool", None, True, False),
        ("capture-tool", "new/tap/capture-tool", "old/tap/capture-tool", False, False),
    ])
    def test_brew_reconciliation_preserves_tap_identity(self, desired, installed, previous, install, uninstall):
        self.run_command([
            "yq", "-i", ".homebrew.formulas.desktop = " + json.dumps([desired]), str(self.manifest),
        ])
        self.installed["formulas"].append(installed)
        self.save_installed()
        if previous:
            self.state.mkdir(parents=True)
            (self.state / "homebrew-formulas.txt").write_text(previous + "\n")
        self.reconcile()
        assert (["brew", "install", "--formula", desired] in self.commands()) == install
        assert (["brew", "uninstall", "--formula", previous] in self.commands()) == uninstall

    def test_command_detection(self):
        definitions = FUNCTIONS.read_text().split("# Source secrets loading function")[0]
        script = definitions + r'''
integer failures=0
check() {
  local expected=$1
  shift
  _dotfiles_is_capturable_install "$@"
  local actual=$?
  if (( actual != expected )); then
    print -r -- "FAIL: $* (expected $expected, got $actual)"
    (( failures += 1 ))
  fi
}
check 0 uv tool install ruff
check 0 uv --color always tool install ruff
check 0 uv tool --color always install ruff
check 0 uv --directory tool tool --project install install ruff
check 0 uv --color=always tool --offline install ruff
check 0 uv tool --cache-dir '/tmp/a b' install ruff
check 0 brew install ripgrep
check 0 brew --verbose install ripgrep
check 0 brew install --cask example
check 1 uv tool list
check 1 uv tool --color always list
check 1 uv tool upgrade ruff
check 1 uv pip install ruff
check 1 uv run tool install ruff
check 1 uv --directory tool install ruff
check 1 uv tool --project install list
check 1 uv tool --color always
check 1 uv tool
check 1 uv
check 1 brew list install
check 1 brew upgrade ripgrep
exit $failures
'''
        self.run_command(["zsh", "-f"], input=script)

    def wrapper_run(self, command, exit_status=0, capture_status=0, interactive=True, spy=True, answers=""):
        # A spy proves invocation without the capture helper's own manager queries.
        if spy:
            self.executable(self.capture_script, f'''#!/bin/sh
printf '%s\\n' "$1" >> "$CAPTURE_TEST_ROOT/captured.txt"
exit {capture_status}
''')
        if exit_status:
            self.env["CAPTURE_TEST_EXIT"] = str(exit_status)
        else:
            self.env.pop("CAPTURE_TEST_EXIT", None)
        definitions = self.root / "wrappers.zsh"
        definitions.write_text(FUNCTIONS.read_text().split("# Source secrets loading function")[0])
        script = f"source {shlex.quote(str(definitions))}\n{command}\nresult=$?\nprint -r -- WRAPPER_STATUS=$result\nexit $result\n"
        if not interactive:
            return subprocess.run(["zsh", "-fc", script], env=self.env, capture_output=True, text=True, timeout=30)
        master, slave = pty.openpty()
        process = subprocess.Popen(
            ["zsh", "-fic", script], env=self.env,
            stdin=slave, stdout=slave, stderr=slave, close_fds=True,
        )
        os.close(slave)
        if answers:
            os.write(master, answers.encode())
        output = bytearray()
        deadline = time.monotonic() + 30
        try:
            while time.monotonic() < deadline:
                if select.select([master], [], [], 0.1)[0]:
                    try:
                        chunk = os.read(master, 65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    output.extend(chunk)
                elif process.poll() is not None:
                    break
            if process.poll() is None:
                process.wait(timeout=1)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            os.close(master)
        return subprocess.CompletedProcess(process.args, process.returncode, output.decode(), "")

    def test_interactive_wrapper_through_real_capture_helper(self):
        self.formula("capture-interactive")
        self.uv_receipt("capture-interactive", '{ name = "capture-interactive", specifier = "==1.2" }')
        for command in ("brew install capture-interactive", "uv tool --color always install capture-interactive"):
            result = self.wrapper_run(command, spy=False, answers="c\n")
            assert result.returncode == 0, result.stdout
            assert "Added capture-interactive" in result.stdout
        assert "capture-interactive" in self.values(".homebrew.formulas.core")
        assert "capture-interactive==1.2" in self.values(".uv.tools.core")

    @pytest.mark.parametrize(("command", "manager"), [
        ("brew --verbose install capture-test", "brew"),
        ("uv tool --color always install capture-test", "uv"),
    ], ids=["brew", "uv"])
    def test_interactive_wrappers_and_exit_status(self, command, manager):
        captured = self.root / "captured.txt"
        result = self.wrapper_run(command, capture_status=9)
        assert result.returncode == 0, result.stdout
        assert captured.read_text() == manager + "\n"
        captured.unlink()
        result = self.wrapper_run(command, exit_status=7)
        assert result.returncode == 7, result.stdout
        assert not captured.exists()
        result = self.wrapper_run(command, interactive=False)
        assert result.returncode == 0, result.stderr
        assert not captured.exists()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, *sys.argv[1:]]))
