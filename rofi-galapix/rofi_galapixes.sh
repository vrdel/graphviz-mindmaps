#!/bin/bash

cd ~/my_notes/galapix/

find -L . -type f -printf '%T@ %p\n' | sort -nr | cut -d' ' -f2- | \
~/.bin/rofi/bin/rofi -i -p "Old Galapixes" -theme gruvbox-dark-soft -dmenu -multi-select \
| xargs -d '\n' -I {} "echo" {} | xargs -d '\n' galaview.sh
