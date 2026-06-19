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


wallpaper="/mnt/sda2/wall/girl_umbrella_road_water_mountain_fence_house.png"
base_cmd="matugen --prefer darkness image $wallpaper"
file="$HOME/.cache/wallchanger/command"
directory="$HOME/.cache/wallchanger/"


if [[ ! -d $directory ]] || [[ ! -f $file ]]; then
  mkdir -p $directory
  echo "$base_cmd" > "$file"
fi

if [[ $# -eq 0 ]]; then
  command=$(<$file)
  eval $command
else
  wallpaper="$1"
  command="matugen --prefer darkness image $wallpaper"
  echo "$command" > "$file"
  eval $command
fi
