vim.pack.add({
    "https://github.com/folke/which-key.nvim",
    "https://github.com/windwp/nvim-autopairs",
    "https://github.com/stevearc/oil.nvim",
    "https://github.com/nvim-tree/nvim-web-devicons",
})

require("nvim-autopairs").setup()
require("oil").setup()
require("nvim-web-devicons").setup()
require("which-key").setup({
    win = { border = "rounded" }
})

-- GUIS
vim.keymap.set("n", "<leader>e", "<Nop>", { desc = "GUIS" })
vim.keymap.set("n", "<leader>ee", "<CMD>Oil<CR>", { desc = "Open Oil File Explorer" })

