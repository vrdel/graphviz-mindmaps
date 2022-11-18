#!/bin/bash

IFS=""
cd ~/my_notes/galapix/vimwiki/
args="$(fzf -m)"

args=$(echo $args | while read line; do echo \"$PWD/$line\"; done)
args=$(echo $args | tr '\n' ' ')

galaview.sh $args
