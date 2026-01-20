#!/bin/bash

cd ~/my_notes/galapix/vimwiki

find -L . -type f -printf '%T@ %p\n' | sort -nr | cut -d' ' -f2- | \
~/.bin/rofi/bin/rofi -i -p "Vimwiki Galapixes" -theme gruvbox-dark-soft -dmenu -multi-select \
| xargs -d '\n' -I {} "echo" {} | xargs -d '\n' galaview.sh
