vim.o.autocomplete = true
vim.diagnostic.config({
  virtual_text = {
    severity = { min = vim.diagnostic.severity.HINT },
  },
  signs = false,
  underline = true,
  update_in_insert = false,
  severity_sort = true,
})

-- LSP keybindings (automatically set when LSP attaches)
vim.api.nvim_create_autocmd('LspAttach', {
  callback = function(args)
    local buf = args.buf
    vim.keymap.set('n', '<leader>g', "<Nop>", { buffer = buf, desc = "LSP" })
    vim.keymap.set('n', '<leader>gd', vim.lsp.buf.definition, { buffer = buf, desc = "LSP Definition" })
    vim.keymap.set('n', 'K', vim.lsp.buf.hover, { buffer = buf, desc = "LSP Hover" })
    vim.keymap.set('n', '<leader>gn', vim.lsp.buf.rename, { buffer = buf, desc = "LSP Rename" })
    vim.keymap.set('n', '<leader>g.', vim.lsp.buf.code_action, { buffer = buf, desc = "Code Action" })
    vim.keymap.set('n', '<leader>gr', vim.lsp.buf.references, { buffer = buf, desc = "LSP References" })
  end,
})

vim.lsp.config("clangd", {
  cmd = { "clangd" },
  filetypes = { 'c', "cpp" },
  root_markers = { ".clangd", "compile_commands.json" }
})
vim.lsp.config("bashls", {
  cmd = { "bash-language-server", "start" },
  filetypes = { 'sh', 'bash' },
  root_markers = { ".git" }
})
vim.lsp.config("pyright", {
  cmd = { "pyright-langserver", "--stdio" },
  filetypes = { 'python' },
  root_markers = { "requirements.txt", "pyproject.toml" }
})
vim.lsp.config("ruff", {
  cmd = { "ruff", "server" },
  filetypes = { 'python' },
  root_markers = { "requirements.txt", "pyproject.toml" }
})
vim.lsp.config("lua_ls", {
  cmd = { "lua-language-server" },
  filetypes = { 'lua' },
  root_markers = { ".git" }
})
vim.lsp.config("qmlls", {
  cmd = { "qmlls6" },
  filetypes = { 'qml', 'qmldir' },
  root_markers = { ".git", "CMakeLists.txt", "qt-project" }
})

vim.lsp.enable("clangd")
vim.lsp.enable("pyright")
vim.lsp.enable("ruff")
vim.lsp.enable("lua_ls")
vim.lsp.enable("bashls")
vim.lsp.enable("qmlls")

-- Auto Complete Fine tuning
vim.opt.complete:append("o")
vim.opt.completeopt = { "menuone", "noselect", "noinsert", "popup" }
vim.o.pumheight = 11
vim.o.pumborder = "rounded"

-- LSP Auto completion
vim.api.nvim_create_autocmd('LspAttach', {
  group = vim.api.nvim_create_augroup('my.lsp', {}),
  callback = function(ev)
    local client = assert(vim.lsp.get_client_by_id(ev.data.client_id))
    if client:supports_method('textDocument/implementation') then
      -- Create a keymap for vim.lsp.buf.implementation ...
    end

    -- Enable auto-completion. Note: Use CTRL-Y to select an item. |complete_CTRL-Y|
    if client:supports_method('textDocument/completion') then
      -- Optional: trigger autocompletion on EVERY keypress. May be slow!
      -- local chars = {}; for i = 32, 126 do table.insert(chars, string.char(i)) end
      -- client.server_capabilities.completionProvider.triggerCharacters = chars

      vim.lsp.completion.enable(true, client.id, ev.buf, { autotrigger = true })
    end

    -- Auto-format ("lint") on save.
    -- Usually not needed if server supports "textDocument/willSaveWaitUntil".
    if not client:supports_method('textDocument/willSaveWaitUntil')
        and client:supports_method('textDocument/formatting') then
      vim.api.nvim_create_autocmd('BufWritePre', {
        group = vim.api.nvim_create_augroup('my.lsp', { clear = false }),
        buffer = ev.buf,
        callback = function()
          vim.lsp.buf.format({ bufnr = ev.buf, id = client.id, timeout_ms = 1000 })
        end,
      })
    end
  end,
})

-- LSP Menu selection
vim.keymap.set('i', '<Tab>', function()
  if vim.fn.pumvisible() == 1 then
    return '<C-n>'
  end
  return '<Tab>'
end, { expr = true })

vim.keymap.set('i', '<S-Tab>', function()
  if vim.fn.pumvisible() == 1 then
    return '<C-p>'
  end
  return '<S-Tab>'
end, { expr = true })

vim.keymap.set('i', '<CR>', function()
  if vim.fn.pumvisible() == 1 then
    return '<C-y>'
  end
  return '<CR>'
end, { expr = true })
