# LLM shell helpers

`please list files by size` suggests a command and places it in the editable
shell buffer. `please -e ...` also requests an explanation. Review the command
before pressing Enter. The prompt uses the current operating system and zsh.

`please` requests a JSON schema with three string fields: `explanation`,
`warning`, and `command`. The selected model and provider must support structured
output. Responses are also validated locally; failed requests or invalid responses
never place a command in the shell buffer.

The `llm` wrapper loads its OpenRouter credential from `keys/openrouter/llm` in
pass. The default model is set by `LLM_MODEL` in `zshrc/00-env.zsh`.

To compare models, try the same prompts with `llm -m MODEL --usage 'PROMPT'`.
When logging is enabled, `llm logs --usage` shows token usage and response duration
(duration requires LLM 0.34+). `llm chat --usage` displays usage after each chat
turn on LLM 0.37+. Token usage depends on what the provider reports; it does not
directly measure cost. `llm logs --short` includes `duration_ms` for comparisons.
