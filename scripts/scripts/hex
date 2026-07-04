#!/bin/bash

if ! pacman -Q python > /dev/null; then
  sudo pacman -S python
fi

python -c "print($1)"
