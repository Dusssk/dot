#!/bin/bash

waybar starts using the matugen cmd
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
cache_dir="$HOME/.cache/wallchanger/"
wall_dir="/mnt/sda2/wall"
mapfile -t wallpapers < <(find $wall_dir -type f -o -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.gif")

wall_amount=$(echo ${#wallpapers[@]})
random_wall_num=$(($RANDOM % ($wall_amount - 1) + 1))

base_cmd="matugen --prefer darkness image ${wallpapers[$random_wall_num]}"
file="$HOME/.cache/wallchanger/command"

for dependency in ${dependencies[@]}; do
  if ! pacman -Q $dependency > /dev/null 2>&1; then
    sudo pacman -S --noconfirm "$dependency"
  fi
done

if [[ ! -d $directory ]] || [[ ! -f $file ]]; then
  mkdir -p $directory
  echo "Exported random wallpaper from '$wall_dir' into '$cache_dir'"
  echo "$base_cmd" > "$file"
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
