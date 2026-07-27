# ~/.config/hypr/modules/monitors.lua

hl.monitor({ output = "HDMI-A-2", mode = "1920x1080@144", position = "1920x0", scale = 1, })
hl.monitor({ output = "HDMI-A-1", mode = "1920x1080", position = "0x0", scale = 1, })

hl.config({
  input = {
    tablet = {
      output = "HDMI-A-2"
    }
  }
})
