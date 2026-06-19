#!/bin/bash

if sudo rm -rf ~/.cache/debuginfod_client/; then
  echo "Cleaned the debuginfod directory"
fi

if sudo pacman -Rns $(pacman -Qdtq); then
  echo "Cleaned up unneeded dependency packages"
fi
