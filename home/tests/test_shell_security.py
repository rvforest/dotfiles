"""Exercise model output through the real shell function without calling an API."""

import json
import os
from pathlib import Path
import subprocess

import pytest


FUNCTIONS = Path(__file__).resolve().parents[1] / "private_dot_config/zsh/zshrc/70-functions.zsh.tmpl"


def run_please(tmp_path, response, llm_status=0):
    # Load only this function, keeping shell startup and real credentials out.
    definition = "function please()" + FUNCTIONS.read_text().split("function please()", 1)[1]
    script = """
setopt promptsubst
llm() { print -r -- "$AUDIT_RESPONSE"; return "$AUDIT_LLM_STATUS"; }
""" + definition + """
please -e list files
result=$?
if read -rz queued; then
  print -r -- "QUEUED=$queued"
fi
exit $result
"""
    return subprocess.run(
        ["zsh", "-f"], input=script, text=True, capture_output=True, timeout=15,
        env={**os.environ, "AUDIT_RESPONSE": response, "AUDIT_LLM_STATUS": str(llm_status),
             "AUDIT_MARKER": str(tmp_path / "executed")},
    )


@pytest.mark.parametrize("field", ["explanation", "warning"])
def test_model_output_is_displayed_literally(tmp_path, field):
    text = '$(printf bad > "$AUDIT_MARKER") `printf bad > "$AUDIT_MARKER"` %F{red} \\n'
    response = {"command": "printf safe-command", "explanation": "", "warning": "", field: text}
    result = run_please(tmp_path, json.dumps(response))
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "executed").exists()
    assert text in result.stdout
    assert "QUEUED=printf safe-command" in result.stdout


@pytest.mark.parametrize("response", [
    "not json",
    '{"command": "printf safe"}',
    '{"command": {}, "warning": "", "explanation": ""}',
    '{"command": "  ", "warning": "", "explanation": ""}',
    '{"command": "printf safe", "warning": "", "explanation": null}',
    '{"command": "printf safe", "warning": "", "explanation": ""}\n'
    '{"command": "printf other", "warning": "", "explanation": ""}',
])
def test_invalid_model_response_never_queues_a_command(tmp_path, response):
    result = run_please(tmp_path, response)
    assert result.returncode != 0
    assert "response is invalid" in result.stderr
    assert "QUEUED=" not in result.stdout


def test_failed_model_call_never_queues_a_command(tmp_path):
    response = json.dumps({"command": "printf safe", "warning": "", "explanation": ""})
    result = run_please(tmp_path, response, llm_status=1)
    assert result.returncode != 0
    assert "Could not generate" in result.stderr
    assert "QUEUED=" not in result.stdout
