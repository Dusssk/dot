vim.pack.add({
  "https://github.com/folke/which-key.nvim",
  "https://github.com/windwp/nvim-autopairs",
  "https://github.com/stevearc/oil.nvim",
  "https://github.com/nvim-tree/nvim-web-devicons",
  "https://github.com/RRethy/base16-nvim",
})

require("nvim-autopairs").setup()
require("nvim-web-devicons").setup()
require("which-key").setup({
  win = { border = "rounded" }
})

-- GUIS
vim.keymap.set("n", "<leader>e", "<Nop>", { desc = "GUIS" })
vim.keymap.set("n", "<leader>ee", "<CMD>Oil<CR>", { desc = "Open Oil File Explorer" })

-- OIL
require("oil").setup({
  default_file_explorer = true,
  columns = {
    "icon",
    "permissions",
    "size",
    "mtime",
  },
  view_options = {
    show_hidden = true,
  },
  keymaps = {
    ["g?"] = { "actions.show_help", mode = "n" },
    ["<C-s>"] = { "actions.select", opts = { vertical = true } },
    ["<C-h>"] = { "actions.select", opts = { horizontal = true } },
    ["<C-t>"] = { "actions.select", opts = { tab = true } },
    ["<C-c>"] = { "actions.close", mode = "n" },
    ["<C-l>"] = "actions.refresh",
    ["-"] = { "actions.parent", mode = "n" },
    ["_"] = { "actions.open_cwd", mode = "n" },
    ["`"] = { "actions.cd", mode = "n" },
    ["g~"] = { "actions.cd", opts = { scope = "tab" }, mode = "n" },
    ["gs"] = { "actions.change_sort", mode = "n" },
    ["gx"] = "actions.open_external",
    ["g."] = { "actions.toggle_hidden", mode = "n" },
    ["g\\"] = { "actions.toggle_trash", mode = "n" },
    -- Open: PDFs with zathura, everything else default
    ["<CR>"] = {
      callback = function()
        local entry = require("oil").get_cursor_entry()
        if entry then
          local dir = require("oil").get_current_dir()
          local path = dir .. entry.name
          local ext = vim.fn.fnamemodify(path, ":e"):lower()
          if ext == "pdf" then
            vim.fn.jobstart({ "zathura", path }, { detach = true })
          else
            require("oil.actions").select.callback()
          end
        end
      end,
    },
  },
  use_default_keymaps = false,
})
