vim.g.mapleader = " "
vim.g.maplocalleader = " "

require("config.keybinds")
require("config.autocmds")
require("config.options")
require("config.plugins")
require("config.colors")
require("config.matugen")
require("config.lsp")

-- Man pages
-- vim.cmd("runtime! plugin/man.lua")
-- vim.g.man_hardwrap = false
-- vim.opt.helpheight = 9999


-- Main TUI
vim.opt.winborder = 'rounded'
