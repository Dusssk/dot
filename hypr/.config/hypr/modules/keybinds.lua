-- ~/.config/hypr/modules/keybinds.lua

-- Modifiers
local mainMod = "SUPER +"
local shiftMod = "SUPER SHIFT +"
local altMod = "SUPER ALT +"

-- Applications
local terminal = "kitty"
local fileManager = "thunar"
local menu = "rofi -show drun"

-- General
hl.bind(mainMod .. "T", hl.dsp.exec_cmd("exec"))
hl.bind(mainMod .. "Q", hl.dsp.exec_cmd("killactive"))
hl.bind(mainMod .. "M", hl.dsp.exec_cmd("~/.config/rofi/launchers/powermenu.sh"))
hl.bind(mainMod .. "E", hl.dsp.exec_cmd(fileManager))
hl.bind(mainMod .. "V", hl.dsp.exec_cmd("cliphist list | rofi -dmenu | cliphist decode | wl-copy"))
hl.bind(mainMod .. "R", hl.dsp.exec_cmd(menu))

hl.bind(shiftMod .. "S", hl.dsp.exec_cmd("hyprshot -m region --clipboard-only"))

-- Window
hl.bind(mainMod, hl.dsp.exec_cmd("hyprctl dispatch togglefloating && hyprctl dispatch centerwindow"))
hl.bind(mainMod .. "mouse:272", hl.dsp.window.drag(), { mouse = true, drag = true })
hl.bind(mainMod .. "mouse:273", hl.dsp.window.float(), { mouse = true, click = true })

hl.bind(mainMod .. "h", { action = "movefocus", direction = "l" })
hl.bind(mainMod .. "j", { action = "movefocus", direction = "d" })
hl.bind(mainMod .. "k", { action = "movefocus", direction = "u" })
hl.bind(mainMod .. "l", { action = "movefocus", direction = "r" })

hl.bind(shiftMod .. "h", { action = "movewindow", direction = "l" })
hl.bind(shiftMod .. "j", { action = "movewindow", direction = "d" })
hl.bind(shiftMod .. "k", { action = "movewindow", direction = "u" })
hl.bind(shiftMod .. "l", { action = "movewindow", direction = "r" })

hl.binds = {
  binds = {
    -- Workspace switching (1-9)
    ...create_workspace_binds(mainMod, "workspace", 1, 9),
    ...create_workspace_binds(shiftMod, "movetoworkspace", 1, 9),
    ...create_workspace_binds(altMod, "movetoworkspacesilent", 1, 9),

    -- Mouse workspace switching
    { mod = mainMod, mouse = "down", action = "workspace", direction = "e+1" },
    { mod = mainMod, mouse = "up",   action = "workspace", direction = "e-1" }
  }
}

-- Helper function for workspace binds
function create_workspace_binds(mod, action, start, finish)
  local binds = {}
  for i = start, finish do
    table.insert(binds, {
      mod = mod,
      key = tostring(i),
      action = action,
      workspace = i
    })
  end
  return binds
end

-- Unbinds
unbinds = {
  { mod = "SUPER", key = "J" },
  { mod = "SUPER", key = "K" }
}
