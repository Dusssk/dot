#!/bin/bash

# waybar starts using the matugen cmd
if pgrep waybar; then
  pkill waybar
fi

if pgrep hyprpaper; then
  pkill hyprpaper
  hyprpaper &
else
  hyprpaper &
fi

dependencies=("waybar" "hyprpaper" "matugen" "imagemagick")
cache_dir="$HOME/.cache/wallchanger"
wall_dir="/mnt/sda2/wall"
mapfile -t wallpapers < <(find $wall_dir -type f -o -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif")
resolution="100x100"
rofi_theme="$HOME/scripts/dependencies/wall/rofi-menu.rasi"

wall_amount=$(echo ${#wallpapers[@]})
random_wall_num=$(($RANDOM % ($wall_amount) + 0))

base_cmd="matugen --prefer darkness image ${wallpapers[$random_wall_num]}"
file="$cache_dir/command"

for dependency in ${dependencies[@]}; do
  if ! pacman -Q $dependency > /dev/null; then
    sudo pacman -S --noconfirm "$dependency"
  fi
done
echo $file

if [[ ! -d $cache_dir ]] || [[ ! -f $file ]]; then
  mkdir -p $cache_dir
  echo "Exported random wallpaper from '$wall_dir' into '$cache_dir'"
  echo "$base_cmd" > "$file"
fi

if [[ "$wall_amount" -eq 0 ]]; then
  notify-send "ERROR: No wallpapers found at $wall_dir"
  exit 1
fi

if [[ $# -eq 0 ]]; then
  command=$(<$file)
  echo "Loaded wallpaper from $file"
  eval $command
else
  wallpaper="$1"
  command="matugen --prefer darkness image $wallpaper"
  echo "$command" > "$file"
  echo "Loaded wallpaper from input: $wallpaper"
  eval $command
fi

# rofi_input=""
# for image in "${wallpapers[@]}"; do
#   basename=$(basename $image)
#   thumbnail="$cache_dir/${basename}.png"
#
#   if [[ ! -f "$thumbnail" ]]; then
#     convert "$image" -auto-orient -thumbnail "${resolution}^" -gravity center -extent "$resolution" "$thumbnail"
#     rofi_input+="${basename}\0icon\x1f${resolution}\x1finfo\x1f${thumbnail}\n"
#   fi
#
#
# SELECTED_INDEX=$(echo -en "$rofi_input" | rofi -dmenu \
#     -i \
#     -show-icons \
#     -theme "$rofi_theme" \
#     -p "Choose wallpaper" \
#     -format 'i' \
#     -selected-row 0
# )
