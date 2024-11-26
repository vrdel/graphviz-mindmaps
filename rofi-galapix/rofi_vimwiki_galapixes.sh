#!/bin/bash

cd ~/my_notes/galapix/vimwiki

find . -type l | sed "s/\/\//\//" | sort | \
~/.bin/rofi/bin/rofi -i -p "Vimwiki Galapixes" -theme gruvbox-dark-soft -dmenu -multi-select \
| xargs -d '\n' -I {} "echo" {} | xargs -d '\n' galaview.sh
