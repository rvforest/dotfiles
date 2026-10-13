"""Offline CLI contract checks. Run: python3 -m unittest discover -s tests."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "home/dot_local/bin/executable_decide"
HELPER = ROOT / "home/private_dot_config/direnv/lib/secrets.sh"


class DecideTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        mock_bin = self.directory / "bin"
        mock_bin.mkdir()
        config = self.directory / "config"
        helper_dir = config / "direnv/lib"
        helper_dir.mkdir(parents=True)
        shutil.copyfile(HELPER, helper_dir / "secrets.sh")
        self.env = dict(os.environ, PATH=f"{mock_bin}:{os.environ['PATH']}",
                        XDG_CONFIG_HOME=str(config), TMPDIR=str(self.directory),
                        MOCK_DIR=str(self.directory))
        self.write_mock(mock_bin / "pass", '''#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$MOCK_DIR/pass.calls"
[[ ${MOCK_SECRET_FAILURE:-0} == 0 ]] || exit 1
printf '%s\\n' "${MOCK_KEY:-test-key}"
''')
        self.write_mock(mock_bin / "curl", '''#!/usr/bin/env python3
import json, os, pathlib, stat, sys
p = pathlib.Path(os.environ["MOCK_DIR"])
a = sys.argv[1:]
def value(flag): return a[a.index(flag) + 1]
headers = pathlib.Path(value("--header")[1:])
request = pathlib.Path(value("--data-binary")[1:])
(p / "curl.capture").write_text(json.dumps({
    "argv": a, "request": json.loads(request.read_text()),
    "headers": headers.read_text(),
    "permissions": stat.S_IMODE(headers.stat().st_mode),
    "request_path": str(request),
}))
pathlib.Path(value("--output")).write_text(os.environ.get("MOCK_RESPONSE",
    '{"answers":{"answer":{"type":"noul","noul":0.99}},"model":"test","usage":{}}'))
sys.exit(int(os.environ.get("MOCK_CURL_STATUS", "0")))
''')
        self.questions = self.directory / "questions.json"
        self.questions.write_text(json.dumps({
            "refund": {"type": "noul", "instructions": "Does this request a refund?"},
            "team": {"type": "choice", "instructions": "Which team?",
                     "criteria": {"billing": "Payments", "other": None}},
            "urgency": {"type": "score", "instructions": "How urgent?",
                        "criteria": ["Low", "High"]},
        }))

    @staticmethod
    def write_mock(path, body):
        path.write_text(body)
        path.chmod(0o755)

    def run_cli(self, *args, state="Please refund me.\n", **env):
        return subprocess.run(["bash", str(COMMAND), *args], input=state,
                              text=True, capture_output=True, env=dict(self.env, **env))

    def assert_no_external_call(self):
        self.assertFalse((self.directory / "pass.calls").exists())
        self.assertFalse((self.directory / "curl.capture").exists())

    def test_dry_run_preserves_text_and_selects_model(self):
        state = 'Quotes: "hi"; backslash: \\; unicode: café\n\n'
        result = self.run_cli("--questions", str(self.questions), "--model",
                              "cloudflare/clef-flash", "--dry-run", state=state)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["state"], state)
        self.assertEqual(payload["model"], "cloudflare/clef-flash")
        self.assertEqual(payload["questions"], json.loads(self.questions.read_text()))
        self.assert_no_external_call()

    def test_json_state_is_one_value_not_a_batch(self):
        for state in ['{"body":"refund"}', '[{"a":1},{"b":2}]', '"hello"']:
            with self.subTest(state=state):
                result = self.run_cli("--dry-run", "--state-format", "json", "Is it urgent?", state=state)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["state"], json.loads(state))

    def test_direct_question_and_dash_escape(self):
        result = self.run_cli("--dry-run", "--", "-- Is this urgent?")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["questions"], {
            "answer": {"type": "noul", "instructions": "-- Is this urgent?"}})

    def test_invalid_state_never_loads_key(self):
        for state, fmt in [("", "text"), (" \n", "text"), ("broken", "json"),
                           ("{} {}", "json"), ("true", "json"), ("null", "json"), ("1", "json")]:
            with self.subTest(state=state):
                result = self.run_cli("--state-format", fmt, "Is it urgent?", state=state)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, "")
        self.assert_no_external_call()

    def test_invalid_questions_never_load_key(self):
        invalid = ["", "{} {}", "{}", "[]", "null", '{"q":{"type":"unknown","instructions":"Q"}}',
                   '{"q":{"type":"choice","instructions":"Q","criteria":{"one":null}}}',
                   '{"q":{"type":"score","instructions":"Q","criteria":["one"]}}',
                   '{"q":{"type":"noul","instructions":" "}}']
        for body in invalid:
            with self.subTest(body=body):
                self.questions.write_text(body)
                result = self.run_cli("-q", str(self.questions))
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, "")
        self.assert_no_external_call()

    def test_invalid_cli(self):
        for args in [[], ["--model"], ["--timeout", "0", "Q"], ["--state-format", "yaml", "Q"],
                     ["--bad"], ["Q", "Q2"], ["--questions", "-"],
                     ["--questions", str(self.questions), "Q"]]:
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 2, result.stderr)
        self.assert_no_external_call()

    def test_success_loads_shared_secret_and_cleans_up(self):
        result = self.run_cli("--timeout", "15", "Is it urgent?")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout)["answers"]["answer"]["noul"], 0.99)
        captured = json.loads((self.directory / "curl.capture").read_text())
        self.assertEqual((self.directory / "pass.calls").read_text(), "show keys/openrouter\n")
        self.assertEqual(captured["headers"], "Authorization: Bearer test-key\n")
        self.assertEqual(captured["permissions"], 0o600)
        self.assertNotIn("test-key", " ".join(captured["argv"]))
        self.assertEqual(captured["argv"][0], "--disable")
        self.assertEqual(captured["argv"][captured["argv"].index("--max-time") + 1], "15")
        self.assertFalse(Path(captured["request_path"]).exists())

    def test_secret_failure_and_multiline_key_do_not_call_api(self):
        for env in [{"MOCK_SECRET_FAILURE": "1"}, {"MOCK_KEY": "key\ninjected"}]:
            result = self.run_cli("Q", **env)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertFalse((self.directory / "curl.capture").exists())

    def test_http_and_transport_failures_keep_stdout_empty(self):
        for status in [22, 28]:
            with self.subTest(status=status):
                result = self.run_cli("Q", MOCK_CURL_STATUS=str(status),
                                      MOCK_RESPONSE='{"error":{"message":"failure"}}')
                self.assertEqual(result.returncode, status)
                self.assertEqual(result.stdout, "")
                self.assertIn("failure", result.stderr)
                captured = json.loads((self.directory / "curl.capture").read_text())
                self.assertFalse(Path(captured["request_path"]).exists())

    def test_invalid_success_response(self):
        for response in ["not JSON", "{}", '{"answers":{},"error":{"message":"bad"}}',
                         '{"answers":{}} {"answers":{}}']:
            with self.subTest(response=response):
                result = self.run_cli("Q", MOCK_RESPONSE=response)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout, "")

    def test_help_does_not_require_input_or_credentials(self):
        result = self.run_cli("--help", state="")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stdout)
        self.assert_no_external_call()


if __name__ == "__main__":
    unittest.main()
