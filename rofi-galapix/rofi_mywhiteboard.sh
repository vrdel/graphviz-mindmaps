#!/bin/bash

cd ~/my_notes/my-whiteboard/

find . -type l | sed "s/\/\//\//" | sort | \
~/.bin/rofi/bin/rofi -i -p "My Whiteboards" -theme gruvbox-dark-soft -dmenu -multi-select \
| xargs -d '\n' -I {} "echo" {} | xargs -d '\n' galaview.sh
