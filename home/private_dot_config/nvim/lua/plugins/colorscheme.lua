return {
  "marko-cerovac/material.nvim",
  name = "material", -- This is important for LazyVim to recognize the plugin
  priority = 1000, -- Ensures it loads before other plugins that might depend on it
  config = function()
    -- Set the global variable *before* loading the colorscheme
    vim.g.material_style = "palenight"

    -- Load the colorscheme
    vim.cmd.colorscheme("material")
  end,
}
