#!/bin/bash

IFS=""
CONTNAME="galapix"

docker rm ${CONTNAME} &>/dev/null; \
docker run \
--cap-add=SYS_ADMIN \
--device /dev/snd \
--device /dev/dri \
-e "DISPLAY=unix$DISPLAY" \
--log-driver json-file \
--log-opt max-size=10m \
-v /dev/log:/dev/log \
-v /dev/dri:/dev/dri \
-v /dev/snd:/dev/snd \
-v /etc/localtime:/etc/localtime \
-v /tmp/.X11-unix:/tmp/.X11-unix \
-v $HOME/.zsh_history:/home/user/.zsh_history \
-h docker-galapix \
--net host \
-u user \
--name ${CONTNAME} \
--rm -ti \
ipanema:5000/galapix:latest /bin/zsh
