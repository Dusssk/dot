#!/bin/bash

packages=("file" "strings" "objdump" "readelf" "ldd" "gdb" "gcore")

for package in "${packages[@]}" do
  if ! pacman -Q $package > /dev/null; then
    sudo pacman -S --noconfirm "$package"
  fi
done
