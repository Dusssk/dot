-- ~/.config/hypr/modules/keybinds.lua

-- Modifiers
local mainMod = "SUPER"
local shiftMod = "SUPER SHIFT"
local altMod = "SUPER ALT"

-- Applications
local terminal = "kitty"
local fileManager = "thunar"
local menu = "rofi -show drun"

hl.bind({
  binds = {
    -- Application launchers
    { mod = mainMod,  key = "T",     action = "exec",        cmd = terminal },
    { mod = mainMod,  key = "Q",     action = "killactive" },
    { mod = mainMod,  key = "M",     action = "exec",        cmd = "~/.config/rofi/launchers/powermenu.sh" },
    { mod = mainMod,  key = "E",     action = "exec",        cmd = fileManager },
    { mod = mainMod,  key = "V",     action = "exec",        cmd = "cliphist list | rofi -dmenu | cliphist decode | wl-copy" },
    { mod = mainMod,  key = "R",     action = "exec",        cmd = menu },

    -- Screenshot
    { mod = shiftMod, key = "S",     action = "exec",        cmd = "hyprshot -m region --clipboard-only" },

    -- Power commands
    { mod = shiftMod, key = "E",     action = "exec",        cmd = "hyprshutdown --post-cmd \"shutdown -h now\"" },
    { mod = shiftMod, key = "R",     action = "exec",        cmd = "hyprshutdown --post-cmd \"reboot\"" },

    -- Window management
    { mod = mainMod,  key = "Y",     action = "exec",        cmd = "hyprctl dispatch togglefloating && hyprctl dispatch centerwindow" },
    { mod = mainMod,  mouse = "272", action = "movewindow" },
    { mod = mainMod,  mouse = "273", action = "resizewindow" },

    -- Vim navigation (focus)
    { mod = mainMod,  key = "h",     action = "movefocus",   direction = "l" },
    { mod = mainMod,  key = "j",     action = "movefocus",   direction = "d" },
    { mod = mainMod,  key = "k",     action = "movefocus",   direction = "u" },
    { mod = mainMod,  key = "l",     action = "movefocus",   direction = "r" },

    -- Vim navigation (move window)
    { mod = shiftMod, key = "h",     action = "movewindow",  direction = "l" },
    { mod = shiftMod, key = "j",     action = "movewindow",  direction = "d" },
    { mod = shiftMod, key = "k",     action = "movewindow",  direction = "u" },
    { mod = shiftMod, key = "l",     action = "movewindow",  direction = "r" },

    -- Workspace switching (1-9)
    ...create_workspace_binds(mainMod, "workspace", 1, 9),
    ...create_workspace_binds(shiftMod, "movetoworkspace", 1, 9),
    ...create_workspace_binds(altMod, "movetoworkspacesilent", 1, 9),

    -- Mouse workspace switching
    { mod = mainMod, mouse = "down", action = "workspace", direction = "e+1" },
    { mod = mainMod, mouse = "up",   action = "workspace", direction = "e-1" }
  }
})

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
