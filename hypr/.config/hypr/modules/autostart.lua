-- ~/.config/hypr/modules/autostart.lua

hl.on("hyprland.start", function()
  hl.exec_cmd("waybar")
  hl.exec_cmd("hyprpaper")
  hl.exec_cmd("hyprsunset")
  hl.exec_cmd("hyprshot")
  hl.exec_cmd("wl-paste --type text --watch cliphist store")
end)
