vim.g.mapleader = " "
vim.g.maplocalleader = " "

require("config.keybinds")
require("config.autocmds")
require("config.options")
require("config.plugins")
require("config.lsp")

-- Man pages
vim.cmd("runtime! plugin/man.lua")
vim.g.man_hardwrap = false
vim.opt.helpheight = 9999

-- Theme
vim.cmd.colorscheme('catppuccin')

local normal_bg = '#181825'
vim.api.nvim_set_hl(0, 'Normal', { bg = normal_bg })
vim.api.nvim_set_hl(0, 'NormalFloat', { bg = normal_bg })
vim.api.nvim_set_hl(0, 'FloatBorder', { bg = normal_bg })
vim.api.nvim_set_hl(0, 'LspHover', { bg = normal_bg })
vim.api.nvim_set_hl(0, 'NormalNC', { bg = normal_bg })

-- Force true color inside tmux
if vim.env.TMUX then
    vim.opt.termguicolors = true
end

-- -- Main TUI
vim.opt.winborder = 'rounded'
-- vim.api.nvim_set_hl(0, "Normal", {bg = "none"})
-- vim.api.nvim_set_hl(0, "NormalFloat", {bg = "none"})
-- vim.api.nvim_set_hl(0, "SignColumn", {bg = "none"})
-- vim.api.nvim_set_hl(0, "LineNr", {bg = "none"})
--
-- -- LSP hover and signature help
-- vim.api.nvim_set_hl(0, 'NormalFloat', { bg = 'none' })
-- vim.api.nvim_set_hl(0, 'FloatBorder', { bg = 'none' })
-- vim.api.nvim_set_hl(0, 'LspHover', { bg = 'none' })
-- vim.api.nvim_set_hl(0, 'LspSignatureActiveParameter', { bg = 'none' })
--
-- -- LSP diagnostic popups
-- vim.api.nvim_set_hl(0, 'DiagnosticUnnecessary', { bg = 'none' })
-- vim.api.nvim_set_hl(0, 'DiagnosticDeprecated', { bg = 'none' })
--
-- Completion menu
vim.api.nvim_set_hl(0, 'Pmenu', { bg = normal_bg })
vim.api.nvim_set_hl(0, 'PmenuSel', { bg = "#45475a" })  -- Keep selection visible
vim.api.nvim_set_hl(0, 'PmenuSbar', { bg = normal_bg })
vim.api.nvim_set_hl(0, 'PmenuThumb', { bg = normal_bg })
--
-- -- StatusLine
-- vim.api.nvim_set_hl(0, 'StatusLine', { bg = 'none' })
-- vim.api.nvim_set_hl(0, 'StatusLineNC', { bg = 'none' })

