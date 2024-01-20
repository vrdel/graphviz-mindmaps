#!/bin/bash

IFS=""
cd ~/my_notes/galapix/vimwiki/
args="$(fzf -m)"

if [ ! -z "$args" ]
then
	args=$(echo $args | while read line; do echo \"$PWD/$line\"; done)
	args=$(echo $args | tr '\n' ' ')
	galaview.sh $args &
	disown -h
else
	exit 0
fi
