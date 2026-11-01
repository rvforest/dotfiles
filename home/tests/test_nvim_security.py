"""Test the actual selector's cache behavior in isolated Neovim processes."""

import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "private_dot_config/nvim/lua/plugins/python.lua"


def test_existing_environment_is_remembered_without_running_uv(tmp_path):
    nvim = shutil.which("nvim")
    plugin = Path(os.environ.get(
        "NVIM_VENV_SELECTOR_PATH", str(Path.home() / ".local/share/nvim/lazy/venv-selector.nvim"),
    ))
    if not nvim or not plugin.is_dir():
        pytest.skip("Requires Neovim and the configured venv-selector revision")
    pinned = re.search(r'commit = "([a-f0-9]+)"', SPEC.read_text())[1]
    installed = subprocess.check_output(["git", "-C", str(plugin), "rev-parse", "HEAD"], text=True).strip()
    assert installed == pinned, "Test the configured selector revision"

    project = tmp_path / "project"
    project.mkdir()
    interpreter = project / ".venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text("#!/bin/sh\nexit 99\n")
    interpreter.chmod(0o700)
    script = project / "example.py"
    script.write_text('# /// script\n# dependencies = ["audit-must-not-be-installed"]\n# ///\n')
    cache = tmp_path / "cache/selected.json"
    env = {**os.environ, "AUDIT_PYTHON_SPEC": str(SPEC), "AUDIT_SELECTOR_PATH": str(plugin),
           "AUDIT_CACHE": str(cache), "AUDIT_PYTHON": str(interpreter), "AUDIT_SCRIPT": str(script),
           "XDG_CONFIG_HOME": str(tmp_path / "config"), "XDG_DATA_HOME": str(tmp_path / "data"),
           "XDG_STATE_HOME": str(tmp_path / "state"), "XDG_CACHE_HOME": str(tmp_path / "cache"),
           "NVIM_LOG_FILE": str(tmp_path / "nvim.log")}
    env.pop("VIRTUAL_ENV", None)
    env.pop("CONDA_PREFIX", None)
    for mode in ("select", "restore", "unknown"):
        directory = project
        if mode == "unknown":
            directory = tmp_path / "unknown"
            directory.mkdir()
            other_script = directory / "example.py"
            other_script.write_bytes(script.read_bytes())
            env["AUDIT_SCRIPT"] = str(other_script)
        result = subprocess.run(
            [nvim, "--headless", "-u", "NONE", "-n", "-l", str(ROOT / "tests/nvim_python.lua")],
            cwd=directory, env={**env, "AUDIT_MODE": mode}, capture_output=True, text=True, timeout=20,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    assert cache.is_file()
    assert not (project / "uv.lock").exists()
    assert not (tmp_path / "unknown/.venv").exists()
