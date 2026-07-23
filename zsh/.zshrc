# ~/.zshrc

# History
HISTFILE="$HOME/.config/zsh/history"
HISTSIZE=100000
SAVEHIST=100000

setopt APPEND_HISTORY
setopt SHARE_HISTORY
setopt HIST_IGNORE_DUPS
setopt HIST_IGNORE_SPACE
setopt HIST_EXPIRE_DUPS_FIRST
setopt HIST_FIND_NO_DUPS

# Shell
setopt AUTOCD
setopt NOBEEP
setopt NUMERIC_GLOB_SORT
bindkey -v

# Load completion system
autoload -Uz compinit && compinit   # Enable smart completion

alias ls="ls --color"
alias cat="bat"
alias objdump="objdump --visualize-jumps --disassembler-color=on"

# Completion with cached metadata file
compinit -d "$XDG_CACHE_HOME/zsh/zcompdump"

# Interactive completion menu
zstyle ':completion:*' menu select

# Case insensitive
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Za-z}'

eval "$(starship init zsh)"

# Hyprland on startup
if [ -z "$WAYLAND_DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    exec Hyprland
fi

source /usr/share/fzf/key-bindings.zsh
source /usr/share/fzf/completion.zsh

