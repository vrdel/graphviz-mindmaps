#!/bin/bash

cd ~/my_notes/galapix
galaview.sh $((find . -type l ; find . -type f) | grep -v '*vimwiki*' | fzf -m)
