# 💤 LazyVim

A starter template for [LazyVim](https://github.com/LazyVim/LazyVim).
Refer to the [documentation](https://lazyvim.github.io/installation) to get started.

# Python projects

Start Neovim from the project directory after creating its environment with
`uv sync` (or another environment manager). Open a Python file and use
`<leader>cv` / `:VenvSelect` to choose the existing environment once. The
selector remembers that choice for the working directory and restores it when
the Python language server attaches on later visits. Use the selector again
after changing environments.

LazyVim's Python extra provides Pyright and Ruff. Neovim itself runs directly;
opening a file does not synchronize Python dependencies. The selector is pinned
to a reviewed revision before automatic PEP 723 environment creation was added.
Review that behavior before updating the pin. Its search stays within the current
project; choose environments only for projects you trust.
