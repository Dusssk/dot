-- ~/.config/hypr/modules/visual.lua

local colors = require("modules.colors")

hl.config({
  general = {
    gaps_in = 4,
    gaps_out = 4,
    border_size = 2,

    col = {
      inactive_border = colors.background,
      active_border = colors.inverse_primary,
    }
  },

  misc = {
    font_family = "FiraCode Nerd Font"
  },

  decoration = {
    rounding = 11,

    blur = {
      enabled = true,
      size = 7,
      passes = 2,
      ignore_opacity = true,

      contrast = 2,

      xray = false,
      new_optimizations = true,
    }
  },
})
