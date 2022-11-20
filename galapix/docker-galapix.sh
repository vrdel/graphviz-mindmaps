#!/bin/bash

IFS=""
CONTNAME="galapix"

function run_existing_container()
{
	docker exec ${CONTNAME} $*
}

function run_new_container()
{
	docker rm ${CONTNAME} &>/dev/null; \
	docker run \
	--cap-add=SYS_ADMIN \
	--device /dev/snd \
	--device /dev/dri \
	-e "DISPLAY=unix$DISPLAY" \
	--log-driver json-file \
	--log-opt max-size=10m \
	-v $HOME/:/home/user/ \
	-v /dev/log:/dev/log \
	-v /dev/dri:/dev/dri \
	-v /dev/snd:/dev/snd \
	-v /etc/localtime:/etc/localtime \
	-v /tmp/.X11-unix:/tmp/.X11-unix \
	-v $HOME/.zsh_history:/home/user/.zsh_history \
	-h docker-${CONTNAME} \
	--net host \
	-u user \
	--name ${CONTNAME} \
	--rm \
	ipanema:5000/galapix:latest $*
}

if docker ps -f name=${CONTNAME} -f status=running -q | grep -q '[0-9a-z]*'
then
	run_existing_container $*
else
	run_new_container $*
fi
