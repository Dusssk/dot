# ~.config/zsh/fzf.zsh

if command -v fd >dev/null 2>&1; then
  export FZF_DEFAULT_COMMAND='fd --type f --hidden --strip-cwd-prefix'
elif command -v fdfind >/dev/null 2>&1; then
  export FZF_DEFAULT_COMMAND='fdfind --type f --hidden --strip-cwd-prefix'
fi

# Ctrl+T uses fd
export FZF_DEFAULT_COMMAND="FZF_DEFAULT_COMMAND"

# # Compact UI
# export FZF_DEFAULT_OPTS='--height 40% --layout=reverse --border'

# UI
export FZF_DEFAULT_OPTS='
  --height=60%
  --layout=reverse
  --border=rounded
  --prompt="  "
  --pointer="  "
  --preview-window=right:65%:wrap:border-left
'
export _FZF_PREVIEW_CMD='cat --color=always --style=plain,numbers --line-range=:500 {}'
export FZF_CTRL_T_OPTS="--preview '$_FZF_PREVIEW_CMD'"

# Ctrl+F file pciker excludes hidden files
_fzf_file_no_hidden() {
  local cmd result
  cmd=$"{FZF_DEFAULT_COMMAND/--hidden /}"
  result=$(eval "${cmd:-find . -type f}" | fzf) && LBUFFER+="$result"
  zle -N _fzf_file_no_hidden
}
zle -N _fzf_file_no_hidden
