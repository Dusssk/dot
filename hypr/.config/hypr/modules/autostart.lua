-- ~/.config/hypr/modules/autostart.lua

hl.on("hyprland.start", function()
  hl.exec_cmd("~/scripts/wall")
  hl.exec_cmd("hyprsunset")
  hl.exec_cmd("goxlr-launcher")
  hl.exec_cmd("hyprshot")
  hl.exec_cmd("wl-paste --type text --type image --watch cliphist store")
end)

hl.on("hyprland.shutdown", function()
  hl.exec_cmd("~/scripts/cleanup")
end)
