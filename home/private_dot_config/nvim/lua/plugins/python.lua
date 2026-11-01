return {
  { import = "lazyvim.plugins.extras.lang.python" },
  {
    "linux-cultist/venv-selector.nvim",
    -- Later revisions automatically run `uv sync` for PEP 723 scripts.
    -- Keep existing-env selection/caching; review that behavior before updating.
    commit = "fe6b3fc697e23707043aa8290da6a28d302996df", -- pragma: allowlist secret (public commit)
    opts = {
      options = {
        enable_cached_venvs = true,
        cached_venv_automatic_activation = true,
        enable_default_searches = false,
      },
      search = {
        -- Search the current project without interpolating its path into a shell
        -- command, or scanning unrelated environments across the Pi.
        project = {
          command = "$FD '/bin/python$' . --full-path --color never -HI -a -L -E .git -E site-packages",
        },
      },
    },
  },
}
