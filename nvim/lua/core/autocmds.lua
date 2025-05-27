-- Autocommands for filetypes
vim.api.nvim_create_autocmd({"BufRead", "BufNewFile"}, {
  pattern = "*.md",
  command = "set filetype=markdown"
})

vim.api.nvim_create_autocmd("FileType", {
  pattern = "markdown",
  command = "set wrap breakindent"
})

vim.api.nvim_create_autocmd("FileType", {
  pattern = "markdown",
  command = "set formatoptions+=1 nolist lbr"
})

vim.api.nvim_create_autocmd("FileType", {
  pattern = "markdown",
  command = "set showbreak=... spell spelllang=en_us"
})

vim.api.nvim_create_autocmd("FileType", {
  pattern = "sh",
  command = "setlocal shiftwidth=4 tabstop=4 expandtab"
})

vim.api.nvim_create_autocmd({"BufRead", "BufNewFile"}, {
  pattern = "*.py",
  callback = function()
        vim.opt.expandtab = true
        vim.opt.tabstop = 4
        vim.opt.softtabstop = 4
        vim.opt.shiftwidth = 4
        vim.opt.textwidth = 88
        vim.opt.autoindent = true
        vim.opt.fileformat = "unix"
        vim.opt.colorcolumn = "88"
        vim.fn.matchadd("BadWhitespace", "\\s\\+$")
  end
})

