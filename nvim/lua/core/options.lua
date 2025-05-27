vim.opt.number = true

vim.opt.splitbelow = true
vim.opt.splitright = true

vim.opt.wrap = false
vim.opt.expandtab = true
vim.opt.tabstop = 4
vim.opt.shiftwidth = 4  --number of space for '>>/<<'

-- syncronize the system clipboard with nvim
vim.opt.clipboard = "unnamedplus"

vim.opt.virtualedit = "block"

vim.opt.inccommand = "split"

vim.opt.ignorecase = true

vim.opt.termguicolors = true

vim.cmd 'colorscheme material-darker'

-- Autoindentation settings
vim.opt.autoindent = true            -- Enable autoindent
vim.opt.expandtab = true             -- Use spaces instead of tabs
vim.opt.smarttab = true              -- Smart tabbing
vim.opt.shiftround = true            -- Round indent to multiple of shiftwidth
vim.opt.copyindent = true            -- Copy the indentation of the previous line

-- Backspace settings
vim.opt.backspace = { "indent", "eol", "start" }  -- Allow backspace over indentation, end of line, and start of insert

-- Ruler and status settings
vim.opt.ruler = true                 -- Show cursor position in the status line
vim.opt.showcmd = true               -- Show partial commands in the command line

-- Mouse support
vim.opt.mouse = "a"                  -- Enable mouse support in all modes

-- Hidden buffers and line numbering
vim.opt.hidden = true                -- Allow hidden buffers
vim.opt.number = true                -- Show line numbers

-- Matching parentheses and brackets
vim.opt.showmatch = true             -- Highlight matching parentheses

-- Wild menu and search
vim.opt.wildmenu = true              -- Enable wildmenu (command-line completion)
vim.opt.wildmode = { "list", "longest", "full" }  -- Wildmenu behavior

-- Status line settings
vim.opt.laststatus = 2               -- Always show the status line
vim.opt.statusline = "%F%m%r%h%w\\ {%Y}\\ [%l,%v][%p%%]"  -- Custom status line

-- History, undo, and wildignore settings
vim.opt.history = 1000               -- Set history size
vim.opt.undolevels = 1000            -- Set undo levels
vim.opt.wildignore = { "*.swp", "*.bak", "*.pyc", "*.class" }  -- Ignore certain files in wildmenu

-- Title and bell settings
vim.opt.title = true                 -- Set the terminal title
vim.opt.visualbell = true            -- Enable visual bell
vim.opt.errorbells = false           -- Disable error bells

-- Search settings
vim.opt.hlsearch = true              -- Highlight search results
vim.opt.incsearch = true             -- Incremental search
vim.opt.ignorecase = true            -- Ignore case in searches
vim.opt.smartcase = true             -- Override ignorecase if the search contains uppercase letters

-- Wrapping and list settings
vim.opt.wrap = false                 -- Disable line wrapping
vim.opt.list = true                  -- Show invisible characters (e.g., spaces, tabs)
vim.opt.spell = true                 -- Enable spellchecking

-- Highlight settings
vim.cmd("highlight BadWhitespace ctermfg=red guibg=darkred")
