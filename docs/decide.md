# decide

`decide` evaluates one state against typed questions using OpenRouter's
[Decisions API](https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request).
Chezmoi installs the standalone Bash command at `~/.local/bin/decide`.
It uses the existing `jq`, `curl`, and `pass` tools and loads
`keys/openrouter` through `~/.config/direnv/lib/secrets.sh` (respecting
`XDG_CONFIG_HOME`). It works outside an interactive zsh session.

## Quick questions

```sh
decide 'Does this message explicitly request a refund?' < message.txt
```

A direct question uses `noul` (probability of yes) and names its answer `answer`:

```sh
decide 'Does this message explicitly request a refund?' < message.txt |
  jq '.answers.answer.noul'
```

For a self-contained live example, paste:

```sh
decide 'Does this message explicitly request a refund?' <<'EOF'
Hi, I cancelled my subscription last week but was charged $20 today.
Please return that payment to my card.
EOF
```

## Reusable questions

Save a JSON object of named questions as `triage.json`:

```json
{
  "refund": {
    "type": "noul",
    "instructions": "Does this message explicitly request a refund?"
  },
  "team": {
    "type": "choice",
    "instructions": "Which team should handle this message? Prefer billing when both categories apply.",
    "criteria": {
      "billing": "Charges, invoices, payments, or refunds",
      "technical": "Problems installing or using the product",
      "other": "Neither category fits"
    }
  },
  "urgency": {
    "type": "score",
    "instructions": "How urgently does this message need a response?",
    "criteria": ["Routine", "Time sensitive", "Immediate attention"]
  }
}
```

```sh
decide --questions triage.json < message.txt
decide --model cloudflare/clef-flash --questions triage.json < message.txt
```

The file contains the `questions` object itself. Each question needs nonblank
instructions and a type. `noul` optionally accepts `criteria` with `true` and
`false` descriptions. `choice` needs at least two named criteria; descriptions
can be strings or null. `score` needs at least two ordered descriptions, lowest
to highest. Scores use zero-based level indices; they are not yes probabilities.
Model-specific limits are enforced by the API.

## Inputs and options

State always comes from stdin. Text is the default and preserves its newlines.
JSON mode requires exactly one JSON string, object, or array:

```sh
jq '{subject, body}' message.json |
  decide --state-format json --questions triage.json
decide --state-format json --questions triage.json < message.json
```

A JSON array is one shared state, not a batch of requests. Empty or whitespace-only
strings are rejected. JSON objects and arrays, including empty ones, are preserved.
There is no automatic format detection, file lookup, or interactive input prompt.
JSON follows jq's parsing semantics, including keeping the last duplicate key.

| Option | Behavior |
| --- | --- |
| `-q`, `--questions FILE` | Read named questions from one JSON document; exclusive with a direct question |
| `-m`, `--model ID` | Accept a full OpenRouter ID; default `typesafe/jev-1.13` |
| `--state-format text\|json` | Interpret stdin; default `text` |
| `--timeout SECONDS` | Positive integer total request timeout; default 60 seconds |
| `--dry-run` | Print the assembled request without accessing credentials or the network |
| `-h`, `--help` | Print usage without requiring input or credentials |
| `--` | End options, allowing a direct question beginning with a dash |

`--questions -` is rejected because stdin belongs to state. Process substitution
works when questions are generated dynamically:

```sh
decide --questions <(jq '.questions' experiment.json) < message.txt
decide --dry-run --questions triage.json < message.txt | jq .
```

## Outputs and failures

Success writes the complete response as JSON to stdout, including named answers,
the resolved model, provider, and usage when supplied by OpenRouter. No local log
is written. Use downstream `jq` to select fields; there are no built-in thresholds
or Boolean exit statuses based on the model's answer. A low probability is still a
successful API call.

Diagnostics and failed response bodies go to stderr; stdout stays empty on
failure. Exit statuses:

- `0`: valid response, dry run, or help.
- `2`: invalid arguments, state, or questions.
- `1`: missing dependency/helper, secret failure, or invalid successful response.
- Curl's status for HTTP/transport failures, notably `22` for HTTP errors and
  `28` for timeout.

Input is validated before loading the secret. Request data and the auth header
live in a private temporary directory removed on exit; the key is not passed in
curl's command-line arguments. Curl configuration files are disabled. Each
invocation makes one request, with a 10-second connection timeout and no automatic
retries or redirects. The total timeout starts with curl, after input and secret
loading.

The wrapper targets OpenRouter's common decision interface, rather than maintaining
a model catalog or provider adapters. Capabilities and confidence calibration vary
by model; switching `--model` does not establish equivalent judgments or thresholds.
Multimodal state can be constructed using JSON mode and the API's documented image
parts; the wrapper does not encode attachments for you. See OpenRouter's
[multimodal guide and provider limits](https://openrouter.ai/docs/guides/community/multimodal-decisions).

## Shell experiments

These examples make live requests using your OpenRouter account. Add `--dry-run`
to a `decide` invocation to inspect its input without making a request; dry-run
output is a request object, so omit downstream filters that select `.answers`.
Examples use Bash/zsh syntax, including process substitution.

### Review a dotfiles patch

From this repo, evaluate an unstaged patch against a focused failure mode:

```sh
git diff -- home |
  decide 'Does this patch introduce a command that will run on every interactive shell startup and access the network, install software, or update a repository? Treat commands inside uncalled function definitions as inactive.' |
  jq '.answers.answer'
```

Use `git diff --cached -- home` for staged changes. With no patch, `decide` rejects
the empty state. Try other narrow questions about repeat installation work or
duplicated machine detection. A patch may omit context needed to judge execution;
use the JSON pattern below to add relevant loader code or machine flags.

### Compare a commit message with its patch

Construct structured state from two shell command outputs:

```sh
jq -n \
  --arg message "$(git log -1 --format=%B)" \
  --arg patch "$(git show --format= --no-ext-diff HEAD)" \
  '{message: $message, patch: $patch}' |
  decide --state-format json \
    'Does the commit message accurately describe the main behavior changed by this patch?' |
  jq '.answers.answer.noul'
```

Replace the message with a deliberately misleading description and compare the
probability. For large inputs, use jq's `--rawfile` to assemble state from files
instead of passing their contents in command-line arguments.

### Classify a failed command's log

Evaluate the likely cause and whether a retry would help in the same request:

```sh
decide --questions <(
  jq -n '{
    cause: {
      type: "choice",
      instructions: "Which category best explains the failure? Prefer unknown when the log lacks enough evidence.",
      criteria: {
        network: "DNS, connectivity, TLS, or remote service failure",
        permissions: "Access denied or insufficient filesystem permissions",
        dependency: "Missing command, package, or incompatible version",
        configuration: "Invalid settings, syntax, or arguments",
        unknown: "Insufficient evidence or another cause"
      }
    },
    retry: {
      type: "noul",
      instructions: "Does the log indicate a transient failure likely to succeed if the same command is retried without changes?"
    }
  }'
) < build.log | jq '.answers'
```

For a self-contained trial, replace `< build.log` with a here-document:

```sh
decide 'Does this log indicate a transient network failure?' <<'EOF'
Downloading package metadata...
curl: (28) Connection timed out after 10000 milliseconds
Package installation aborted before any changes were made.
EOF
```

### Branch on a semantic condition

Let jq turn the returned probability into a shell condition:

```sh
if decide 'Does this report include concrete steps to reproduce the problem, an expected result, and an actual result?' \
    < issue.txt |
    jq -e '.answers.answer.noul >= 0.9' >/dev/null
then
  printf 'Ready for investigation\n'
else
  printf 'Needs review or the evaluation failed\n'
fi
```

The example threshold is for experimentation; evaluate cutoffs on your own labeled
inputs. API failures also enter the `else` branch. To distinguish them from a low
probability, capture and check `decide`'s exit status before evaluating its response.

### Compare models

Keep the state and questions fixed, and select a different model:

```sh
decide --model typesafe/jev-1.13 --questions triage.json < message.txt | jq .
decide --model cloudflare/clef-flash --questions triage.json < message.txt | jq .
decide --model perplexity/pplx-decider-v1.1-27b --questions triage.json < message.txt | jq .
```

Compare chosen labels, probability distributions, and reported usage. Save clear
and ambiguous examples so you can distinguish changes in model behavior from
changes in your input or rubric wording.

## Validation

Offline checks mock `pass` and `curl` while using the repo's actual secrets helper:

```sh
bash -n home/dot_local/bin/executable_decide
shellcheck -x home/dot_local/bin/executable_decide
python3 -B -m unittest discover -s tests -v
```
