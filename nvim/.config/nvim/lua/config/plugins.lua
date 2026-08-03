vim.pack.add({
  "https://github.com/folke/which-key.nvim",
  "https://github.com/windwp/nvim-autopairs",
  "https://github.com/stevearc/oil.nvim",
  "https://github.com/nvim-tree/nvim-web-devicons",
  "https://github.com/RRethy/base16-nvim",
  "https://github.com/mbbill/undotree"
})

require("nvim-autopairs").setup()
require("nvim-web-devicons").setup()
require("which-key").setup({
  win = { border = "rounded" }
})

-- GUIS
vim.keymap.set("n", "<leader>e", "<Nop>", { desc = "GUIS" })
vim.keymap.set("n", "<leader>ee", "<CMD>Oil<CR>", { desc = "Open Oil File Explorer" })

-- Undo Tree
vim.keymap.set("n", "<leader>eu", "<CMD>UndotreeToggle<CR>", { desc = "Open Undotree" })

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
    ["<C-p>"] = "actions.preview",
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
    -- Open files with appropriate handlers
    ["<CR>"] = {
      callback = function()
        local entry = require("oil").get_cursor_entry()
        if entry then
          local dir = require("oil").get_current_dir()
          local path = dir .. entry.name
          local ext = vim.fn.fnamemodify(path, ":e"):lower()

          -- Video extensions
          local video_extensions = {
            "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v",
            "mpg", "mpeg", "3gp", "ogv", "ts", "mts", "m2ts", "vob"
          }

          -- Audio extensions
          local audio_extensions = {
            "mp3", "flac", "wav", "ogg", "m4a", "aac", "opus", "wma",
            "alac", "ape", "dsf", "dff", "mka", "tak", "tta", "wv"
          }

          -- Image extensions
          local image_extensions = {
            "png", "jpg", "jpeg", "gif", "webp", "bmp", "svg", "tiff", "heic", "avif"
          }

          -- Check if video
          local is_video = false
          for _, video_ext in ipairs(video_extensions) do
            if ext == video_ext then
              is_video = true
              break
            end
          end

          -- Check if audio
          local is_audio = false
          for _, audio_ext in ipairs(audio_extensions) do
            if ext == audio_ext then
              is_audio = true
              break
            end
          end

          -- Check if image
          local is_image = false
          for _, img_ext in ipairs(image_extensions) do
            if ext == img_ext then
              is_image = true
              break
            end
          end

          -- Handle based on file type
          if ext == "pdf" then
            vim.fn.jobstart({ "zathura", path }, { detach = true })
          elseif is_video or is_audio then
            -- Simple MPV command for both video and audio
            vim.fn.jobstart({ "mpv", "--save-watch-history", path }, { detach = true })
          elseif is_image then
            -- Open a new Kitty window with kitten icat
            vim.fn.jobstart({
              "kitty", "sh", "-c",
              "kitty icat " .. vim.fn.shellescape(path) .. " && echo '\n\nPress Enter to close...' && read"
            }, { detach = true })
          else
            require("oil.actions").select.callback()
          end
        end
      end,
    },
  },
  use_default_keymaps = false,
})
