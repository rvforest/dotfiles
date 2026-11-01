local spec = dofile(vim.env.AUDIT_PYTHON_SPEC)
local selector_spec = spec[2]
vim.opt.runtimepath:prepend(vim.env.AUDIT_SELECTOR_PATH)

local opts = vim.deepcopy(selector_spec.opts)
opts.cache = { file = vim.env.AUDIT_CACHE }
-- Verify the selector's interpreter settings with a fake LSP client; this test
-- does not exercise a real language server's import resolution.
local client = { id = 123, settings = {}, notify = function() end }
vim.lsp.get_clients = function(filter)
  return filter.name == "pyright" and { client } or {}
end
-- Selecting/restoring an existing environment must not spawn installers.
vim.system = function() error("unexpected subprocess") end
vim.fn.jobstart = function() error("unexpected job") end

local selector = require("venv-selector")
selector.setup(opts)
vim.cmd.edit(vim.fn.fnameescape(vim.env.AUDIT_SCRIPT))
vim.bo.filetype = "python"
if vim.env.AUDIT_MODE == "select" then
  selector.activate_from_path(vim.env.AUDIT_PYTHON)
else
  vim.api.nvim_exec_autocmds("LspAttach", { buffer = 0, data = { client_id = client.id } })
end

if vim.env.AUDIT_MODE == "unknown" then
  assert(vim.env.VIRTUAL_ENV == nil, "unknown project activated an environment")
  assert(client.settings.python == nil, "unknown project changed the interpreter")
else
  assert(selector.python() == vim.env.AUDIT_PYTHON, "wrong interpreter selected")
  assert(vim.env.VIRTUAL_ENV == vim.fn.fnamemodify(vim.env.AUDIT_PYTHON, ":h:h"))
  assert(client.settings.python.pythonPath == vim.env.AUDIT_PYTHON, "Pyright was not configured")
end
