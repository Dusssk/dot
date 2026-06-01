-- Function to remove trailing whitespace
local function remove_trailing_whitespace()
-- Remove trailing whitespace in the entire buffer
vim.cmd("%s/\\s\\+$//e")

-- Set the highlight group for trailing whitespace to none
vim.cmd("highlight ExtraWhitespace guibg=NONE ctermbg=NONE")
end

-- Auto command to execute the function before saving
vim.api.nvim_create_autocmd("BufWritePre", {
pattern = "*",
callback = remove_trailing_whitespace,
})

-- Highlight yank
vim.api.nvim_create_autocmd("TextYankPost", {
desc = "Highlight when yanking (copying) text",
group = vim.api.nvim_create_augroup("kickstart-highlight-yank", { clear = true }),
callback = function()
vim.highlight.on_yank()
end,
})

-- Formats file on save with LSP
vim.cmd([[
augroup FileFormat
    autocmd!
    autocmd BufWritePre * lua format_and_save()
augroup END
]])

function format_and_save()
-- Check both filetype and buffer type
if vim.bo.filetype == "oil" or vim.bo.buftype == "acwrite" then
-- Just do a silent write and return immediately
vim.cmd("silent! write")
return
end

-- For regular files
vim.lsp.buf.format()
vim.cmd("write")
end

-- Auto reload files when changed externally
vim.api.nvim_create_autocmd({ "FocusGained", "BufEnter" }, {
pattern = "*",
command = "checktime",
})

-- -- Java file
-- vim.api.nvim_create_autocmd("FileType", {
-- pattern = "java",
-- callback = function(args)
-- require("jdtls.jdtls_setup").setup()
-- end,
-- })

