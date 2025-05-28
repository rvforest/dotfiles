local map = vim.keymap.set

-- Set leader key
vim.g.mapleader = " "

-- Normal mode keymaps
map("n", "<leader>ff", ":Telescope find_files<CR>", { silent = true })
map("n", "<leader>bb", ":Telescope buffers<CR>", { silent = true })
map("n", "Y", "y$", { silent = true })
map("n", ";", ":", { silent = true })

-- Insert mode keymaps
map("i", "jk", "<Esc>", { noremap = true })


-- Neogit Mappings
map('n', '<Leader>gs', ':Neogit<CR>', { noremap = true, silent = true })  -- Open Neogit status
map('n', '<Leader>gc', ':Neogit commit<CR>', { noremap = true, silent = true })  -- Git commit
map('n', '<Leader>gp', ':Neogit push<CR>', { noremap = true, silent = true })    -- Git push
map('n', '<Leader>gf', ':Neogit fetch<CR>', { noremap = true, silent = true })   -- Git fetch
map('n', '<Leader>gl', ':Neogit log<CR>', { noremap = true, silent = true })     -- Git log
map('n', '<Leader>gd', ':Neogit diff<CR>', { noremap = true, silent = true })    -- Git diff
map('n', '<Leader>gb', ':Neogit branch<CR>', { noremap = true, silent = true })  -- Git branches



