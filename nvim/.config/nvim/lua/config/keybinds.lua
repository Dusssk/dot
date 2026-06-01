local opts = { noremap = true, silent = true }


-- Move lines up/down with J and K in visual mode
vim.keymap.set("v", "<Up>", ":m '<-2<CR>gv=gv", { desc = "move lines up" })
vim.keymap.set("v", "<Down>", ":m '>+1<CR>gv=gv", { desc = "move lines down" })

-- Indent left/right
vim.keymap.set("v", "<A-l>", ">gv", { desc = "indent right" })
vim.keymap.set("v", "<A-h>", "<gv", { desc = "indent left" })

-- Center search result.
vim.keymap.set("n", "n", "nzzzv")
vim.keymap.set("n", "N", "Nzzzv")

-- Increment text left or right.
vim.keymap.set("v", "<", "<gv", opts)
vim.keymap.set("v", ">", ">gv", opts)

-- Clipboard
-- Paste without replacing clipboard content.
-- vim.keymap.set("x", "<leader>p", [["_dP]])
-- vim.keymap.set("v", "p", '"_dp', opts)
-- vim.keymap.set({ "n", "v" }, "<leader>d", [["_d]])
-- vim.keymap.set("i", "<C-c>", "<Esc>")
-- vim.keymap.set("n", "<C-c>", ":nohl<CR>", { desc = "Clear search hl", silent = true })

-- Copyfilepath to clipboard
-- vim.keymap.set("n", "<leader>yf", function()
-- local filePath = vim.fn.expand("%:~")
-- vim.fn.setreg("+", filePath)
-- print("File path copied to clipboard: " .. filePath)
-- end, { desc = "Copy file path to clipboard" })
-- vim.keymap.set("n", "<leader>f", vim.lsp.buf.format)


vim.keymap.set("n", "<leader>o", "<Nop>", { desc = "Files" })
-- Pdf viewer
vim.keymap.set('n', '<leader>op', function()
    local ok, entry = pcall(require('oil').get_cursor_entry)
    local filepath = nil

    if ok and entry and entry.name then
        -- Get the current directory Oil is browsing
        local oil_dir = require('oil').get_current_dir()
        if oil_dir then
            filepath = oil_dir .. entry.name
        end
    end

    if not filepath then
        filepath = vim.fn.expand('<cfile>')
        if filepath and not filepath:match('^/') then
            filepath = vim.fn.getcwd() .. '/' .. filepath
        end
    end

    if filepath and filepath:match('%.pdf$') then
        if vim.fn.filereadable(filepath) == 1 then
            vim.fn.jobstart({ 'zathura', filepath }, { detach = true })
        else
            vim.notify('File not readable: ' .. filepath, vim.log.levels.ERROR)
        end
    else
        vim.notify('Not a PDF file or no file under cursor', vim.log.levels.WARN)
    end
end, { desc = 'Open PDF in zathura' })

-- Open file in system default application
-- vim.keymap.set('n', '<leader>ox', function()
--     local entry = require('oil').get_cursor_entry()
--     if entry then
--         local dir = require('oil').get_current_dir()
--         local path = dir .. entry.name
--         vim.fn.jobstart({ 'xdg-open', path }, { detach = true })
--     end
-- end, { desc = 'Open externally' })

-- Open terminal in current Oil directory
vim.keymap.set('n', '<leader>ot', function()
    local dir = require('oil').get_current_dir()
    vim.cmd('cd ' .. dir)
    vim.cmd('terminal')
end, { desc = 'Terminal in directory' })

-- Copy file path to clipboard
vim.keymap.set('n', '<leader>oy', function()
    local entry = require('oil').get_cursor_entry()
    if entry then
        local dir = require('oil').get_current_dir()
        local path = dir .. entry.name
        vim.fn.setreg('+', path)
        vim.notify('Copied: ' .. path)
    end
end, { desc = 'Copy path to clipboard' })

-- Disable Middle Mouse Paste
vim.keymap.set('n', '<MiddleMouse>', '<Nop>', { desc = 'Disable middle mouse paste' })
vim.keymap.set('i', '<MiddleMouse>', '<Nop>', { desc = 'Disable middle mouse paste' })
vim.keymap.set('v', '<MiddleMouse>', '<Nop>', { desc = 'Disable middle mouse paste' })

vim.keymap.set("n", "x", '"_x', opts) -- prevents deleted character to gather at clipboard.


-- If __name__ == "__main__": python
vim.keymap.set("n", "<leader>c", "<Nop>", { noremap = true, silent = true, desc = "Code Actions" })
vim.keymap.set("n", "<leader>cp", "<Nop>", { noremap = true, silent = true, desc = "Python" })

vim.api.nvim_set_keymap( "n", "<leader>cpi", "iif __name__ == '__main__':<CR>main()<esc>", { noremap = true, silent = true, desc = 'Pythons if __name__ == "__main__":' })

-- Python boilerplate template
vim.api.nvim_set_keymap(
"n",
"<leader>cpm",
'i\
def main() -> None:<CR>print("Hello world!")<CR><CR><CR><BS>if __name__ == "__main__":<CR>main()<Esc>',
{ noremap = true, silent = true, desc = "Basic Python boilerplate code" }
)

-- Formats file on save with LSP
vim.api.nvim_set_keymap("n", "<C-s>", ":w<CR>", { noremap = true, silent = true })

-- Vertical man page
vim.keymap.set('n', '<leader>ehv', function()
    vim.ui.input({ prompt = 'Man (vertical): ' }, function(input)
        if input and #input > 0 then
            vim.cmd('vertical Man ' .. input)
        end
    end)
end, { desc = 'Man Page (vertical split)' })

-- Man page (current window, full screen)
vim.keymap.set('n', '<leader>ehm', function()
    vim.ui.input({ prompt = 'Man: ' }, function(input)
        if input and #input > 0 then
            vim.cmd('Man ' .. input)
        end
    end)
end, { desc = 'Input Man Page' })

-- Tab man page
vim.keymap.set('n', '<leader>eht', function()
    vim.ui.input({ prompt = 'Man (tab): ' }, function(input)
        if input and #input > 0 then
            vim.cmd('tab Man ' .. input)
        end
    end)
end, { desc = 'Man Page (new tab)' })

vim.keymap.set("n", "<leader>eh", "<Nop>", { desc = "Help Tags & Man Pages" })
vim.keymap.set("n", "<leader>ehl", "<cmd>:help<CR>", { desc = "List Help Tags" })

-- Help tag (current window, full screen)
vim.keymap.set('n', '<leader>ehh', function()
    vim.ui.input({ prompt = 'Input Help Tag: ' }, function(input)
        if input and #input > 0 then
            vim.cmd('help ' .. input)
        end
    end)
end, { desc = 'Input Help Tag' })

-- Vertical help tag
vim.keymap.set('n', '<leader>ehs', function()
    vim.ui.input({ prompt = 'Help Tag (vertical): ' }, function(input)
        if input and #input > 0 then
            vim.cmd('vertical help ' .. input)
        end
    end)
end, { desc = 'Help Tag (vertical split)' })

-- Tab help tag
vim.keymap.set('n', '<leader>ehx', function()
    vim.ui.input({ prompt = 'Help Tag (tab): ' }, function(input)
        if input and #input > 0 then
            vim.cmd('tab help ' .. input)
        end
    end)
end, { desc = 'Help Tag (new tab)' })

-- Clear search highlight
vim.keymap.set('n', '<Esc>', ':nohlsearch<CR>', { desc = 'Clear search highlights' })

vim.keymap.set("v", "<leader>c", "<Nop>", { desc = "Code Actions" })

-- Replacing text (visual selection)
vim.keymap.set('v', '<leader>cw', function()
    local start_line = vim.fn.line('v')
    local end_line = vim.fn.line('.')

    if start_line > end_line then
        start_line, end_line = end_line, start_line
    end

    vim.ui.input({ prompt = 'Replace in selection (Enter to cancel, q to quit): ' }, function(pattern)
        if not pattern or #pattern == 0 or pattern == 'q' then return end

        vim.ui.input({ prompt = 'Replace "' .. pattern .. '" with (Enter to cancel): ' }, function(replacement)
            if not replacement or #replacement == 0 then return end

            local range = start_line .. ',' .. end_line
            local escaped_pattern = vim.fn.escape(pattern, '/\\[]^$.*~')
            local escaped_replacement = vim.fn.escape(replacement, '/\\')
            vim.cmd(range .. 's/' .. escaped_pattern .. '/' .. escaped_replacement .. '/gc')
        end)
    end)
end, { desc = 'Replace in visual selection' })


-- Global visual selection replacement
vim.keymap.set('v', '<leader>cW', function()
    local saved_reg = vim.fn.getreg('"')
    local saved_reg_type = vim.fn.getregtype('"')
    vim.cmd('noautocmd normal! "xy')
    local selection = vim.fn.getreg('x')
    vim.fn.setreg('"', saved_reg, saved_reg_type)

    if selection == '' then
        vim.notify('No text selected', vim.log.levels.WARN)
        return
    end

    vim.ui.input({ prompt = 'Replace "' .. selection .. '" with (Enter to cancel, q to quit): ' }, function(replacement)
        if not replacement or #replacement == 0 or replacement == 'q' then return end

        local escaped_selection = vim.fn.escape(selection, '/\\[]^$.*~')
        local escaped_replacement = vim.fn.escape(replacement, '/\\')
        vim.cmd('%s/' .. escaped_selection .. '/' .. escaped_replacement .. '/gc')
    end)
end, { desc = 'Replace selection across whole file' })


-- Global text replacement
vim.keymap.set('n', '<leader>cw', function()
    local word = vim.fn.expand('<cword>')
    if word == '' then
        vim.notify('No word under cursor', vim.log.levels.WARN)
        return
    end
    vim.ui.input({ prompt = 'Replace "' .. word .. '" with (Enter to cancel, q to quit): ' }, function(input)
        if input and #input > 0 and input ~= 'q' then
            local escaped_word = vim.fn.escape(word, '/\\[]^$.*~')
            local escaped_input = vim.fn.escape(input, '/\\')
            vim.cmd('%s/\\<' .. escaped_word .. '\\>/' .. escaped_input .. '/gc')
        end
    end)
end, { desc = 'Replace word under cursor in file' })


-- Convert buffer into terminal
vim.api.nvim_set_keymap("n", "<leader>eb", "<cmd>term<CR>", { noremap = true, silent = true, desc = "Buffer -> Terminal"})

-- Open terminal as vertical buffer
vim.api.nvim_set_keymap("n", "<leader>ev", "<cmd>vertical term<CR>", { noremap = true, silent = true, desc = "Terminal (Vertical)"})

-- Open terminal in new tab
vim.api.nvim_set_keymap("n", "<leader>et", "<cmd>tab term<CR>", { noremap = true, silent = true, desc = "Terminal (Tab)"})

-- Keybind to exit terminal mode
vim.api.nvim_set_keymap("t", "<Esc><Esc>", "<C-\\><C-n>", { noremap = true, silent = true })
-- Activate venv in current directory
vim.api.nvim_set_keymap("t", "<F9>", ".venv\\scripts\\activate<CR>", { noremap = true, silent = true })

-- Diagnostic
vim.keymap.set("n", "<leader>f", "", { desc = "Diagnostic & Symbols" })
vim.keymap.set("n", "<leader>fd", vim.diagnostic.setloclist, { desc = "Diagnostics list" })
-- vim.keymap.set("n", "<leader>fd", vim.diagnostic.open_float, { desc = "Diagnostic" })

-- Symbols
vim.keymap.set("n", "<leader>fs", vim.lsp.buf.document_symbol, { desc = "Document Symbols" })
vim.keymap.set("n", "<leader>fS", vim.lsp.buf.workspace_symbol, { desc = "Workspace Symbols" })

-- Files
vim.keymap.set("n", "<leader>er", ":browse oldfiles<CR>", { desc = "Recent Files" })

-- vim.keymap.set("n", "<leader>fg", ":grep! <cword> .<CR>copen<CR>", { desc = "Grep Word" })
-- vim.keymap.set("n", "<leader>fG", ":grep! ", { desc = "Grep Search" })


-- Buffers
vim.keymap.set("n", "<leader>b", "<Nop>", { desc = "Buffers" })
vim.api.nvim_set_keymap("n", "<leader>bn", ":bnext<CR>", { noremap = true, silent = true, desc = "Next Buffer" })
vim.api.nvim_set_keymap( "n", "<leader>bp", ":bprevious<CR>", { noremap = true, silent = true, desc = "Previous Buffer" })

vim.keymap.set("n", "<leader>bq", function()
    local current_buf = vim.api.nvim_get_current_buf()
    -- Switch to the previous buffer
    vim.cmd("bprevious")
    -- Only delete if we actually switched away (i.e., there was another buffer)
    if vim.api.nvim_get_current_buf() ~= current_buf then
        vim.cmd("bdelete " .. current_buf)
    end
end, { desc = "Remove buffer from list, keep window open" })

vim.keymap.set('n', '<leader>bl', function()
    vim.cmd('ls')
    vim.ui.input({ prompt = 'Buffer number (Enter to cancel, q to quit): ' }, function(input)
        if input and #input > 0 and input ~= 'q' then
            local ok = pcall(function()
                vim.cmd('buffer ' .. input)
            end)
            if not ok then
                vim.notify('Invalid buffer number: ' .. input, vim.log.levels.ERROR)
            end
        end
    end)
end, { desc = 'List Buffers & Switch' })

-- Tabs
vim.keymap.set("n", "<leader>t", "<Nop>", { noremap = true, silent = true, desc = "Tabs" })
vim.keymap.set("n", "<leader>to", "<cmd>tabnew<CR>", { noremap = true, silent = true, desc = "New Tab" })
vim.keymap.set("n", "<leader>tq", "<cmd>tabclose<CR>", { noremap = true, silent = true, desc = "Close Tab" })
vim.keymap.set("n", "<leader>tn", "<cmd>tabn<CR>", { noremap = true, silent = true, desc = "Next Tab" })
vim.keymap.set("n", "<leader>tp", "<cmd>tabp<CR>", { noremap = true, silent = true, desc = "Previous Tab" })
