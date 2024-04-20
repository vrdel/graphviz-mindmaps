#!/bin/bash

target=$(grep "$1" -l Makefile*)
echo $target

if [ -z "$target" ]
then
	echo "$1" not found in any Makefile
else
	echo Found in "$target"
	make -f "$target" "$1"
fi
