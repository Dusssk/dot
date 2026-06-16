# ~/.config/hypr/modules/monitors.lua

hl.monitor({ output = "HDMI-A-1", mode = "1920x1080@60", position = "auto", scale = 1, })
hl.monitor({ output = "HDMI-A-2", mode = "1920x1080@60", position = "0x0", scale = 1, })

hl.config({
  input_tablet = {
    output = "HDMI-A-1"
  },
})
