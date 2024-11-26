#!/bin/bash

cd ~/my_notes/galapix/

find . -type l | sed "s/\/\//\//" | sort | \
~/.bin/rofi/bin/rofi -i -p "Old Galapixes" -theme gruvbox-dark-soft -dmenu -multi-select \
| xargs -d '\n' -I {} "echo" {} | xargs -d '\n' galaview.sh
