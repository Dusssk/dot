# ~/.config/hypr/modules/visual.lua

local colors = require("modules.colors")

hl.config({
  general = {
    gaps_in = 2,
    gaps_out = 11,
    border_size = 2,
    col = {
      inactive_border = colors.background,
      active_border = colors.inverse_primary,
    }
  },

  misc = {
    font_family = "FiraCode Nerd Font"
  },

  -- Decoration
  decoration = {
    rounding = 4
  },
})
