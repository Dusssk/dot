-- ~/.config/hypr/modules/keybinds.lua

-- Modifiers
local mainMod = "SUPER +"
local shiftMod = "SUPER + SHIFT +"
local altMod = "SUPER + ALT +"

-- Applications
local terminal = "kitty"
local fileManager = "thunar"
local menu = "rofi -show drun"

-- General
hl.bind(mainMod .. "T", hl.dsp.exec_cmd("kitty"))
hl.bind(mainMod .. "Q", hl.dsp.window.close())
hl.bind(mainMod .. "M", hl.dsp.exec_cmd("~/.config/rofi/launchers/powermenu.sh"))
hl.bind(mainMod .. "E", hl.dsp.exec_cmd(fileManager))
hl.bind(mainMod .. "V", hl.dsp.exec_cmd("cliphist list | rofi -dmenu | cliphist decode | wl-copy"))
hl.bind(mainMod .. "R", hl.dsp.exec_cmd(menu))

hl.bind(shiftMod .. "S", hl.dsp.exec_cmd("hyprshot -m region --clipboard-only"))

-- Window
hl.bind(mainMod .. "Y", hl.dsp.exec_cmd("hyprctl dispatch togglefloating && hyprctl dispatch centerwindow"))
hl.bind(mainMod .. "F", hl.dsp.window.fullscreen({ mode = toggle }))
hl.bind(mainMod .. "mouse:272", hl.dsp.window.drag(), { mouse = true, drag = true })
hl.bind(mainMod .. "mouse:273", hl.dsp.window.float(), { mouse = true, click = true })

hl.bind(mainMod .. "h", hl.dsp.focus({ direction = "l" }))
hl.bind(mainMod .. "j", hl.dsp.focus({ direction = "d" }))
hl.bind(mainMod .. "k", hl.dsp.focus({ direction = "u" }))
hl.bind(mainMod .. "l", hl.dsp.focus({ direction = "r" }))

hl.bind(shiftMod .. "h", hl.dsp.window.move({ direction = "l" }))
hl.bind(shiftMod .. "j", hl.dsp.window.move({ direction = "d" }))
hl.bind(shiftMod .. "k", hl.dsp.window.move({ direction = "u" }))
hl.bind(shiftMod .. "l", hl.dsp.window.move({ direction = "r" }))

hl.bind(mainMod .. "X", function()
  if hl.get_workspace("special:minimized") then
    hl.dispatch(hl.dsp.window.move({ workspace = hl.get_active_workspace(), window = "tag:minimized" }))
    hl.dispatch(hl.dsp.window.clear_tags({ window = "tag:minimized" }))
  else
    hl.dispatch(hl.dsp.window.tag({ tag = "minimized", window = hl.get_active_window() }))
    hl.dispatch(hl.dsp.window.move({ workspace = "special:minimized", follow = false }))
  end
end)

-- Unbinds
hl.unbind(mainMod .. "J")
hl.unbind(mainMod .. "K")

for i = 1, 10 do
  local key = i % 10 -- 10 maps to key 0
  if is_fr then
    key = fr_keys[i]
  end
  hl.bind(mainMod .. " + " .. key, hl.dsp.focus({ workspace = i }), { description = "Focus workspace " .. i })
  hl.bind(shiftMod .. " + " .. key, hl.dsp.window.move({ workspace = i }),
    { description = "Move window to workspace " .. i })
  -- Silent version (ALT + key)
  hl.bind(altMod .. " + " .. key, hl.dsp.window.move({ workspace = i, follow = false }),
    { description = "Move window to workspace " .. i .. " silently" })
end
