# ~/.zshrc
#
autoload -Uz compinit && compinit   # Enable smart completion
setopt HIST_IGNORE_DUPS             # Don't save duplicate history
setopt AUTOCD                        # cd by typing directory name

eval "$(starship init zsh)"

# Hyprland on startup
if [ -z "$WAYLAND_DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    exec Hyprland
fi

