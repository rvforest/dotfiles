return {
    {
        'marko-cerovac/material.nvim',
    },
    {
        "neovim/nvim-lspconfig",
        config = function()
          require("lspconfig").ruff.setup({}) -- Example LSP setup for Python
        end,
    },
    {
        'nvim-telescope/telescope.nvim', branch = '0.1.x',
          dependencies = { 'nvim-lua/plenary.nvim' }
    },
    {
      "NeogitOrg/neogit",
      dependencies = {
        "nvim-lua/plenary.nvim",         -- required
        "sindrets/diffview.nvim",        -- optional - Diff integration

        -- Only one of these is needed.
        "nvim-telescope/telescope.nvim", -- optional
      },
      config = true
    },
    {
        "lewis6991/gitsigns.nvim"
    },
    {
        "tpope/vim-fugitive"
    },
}
