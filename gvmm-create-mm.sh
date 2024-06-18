#!/bin/bash

IFS=""

TEMPLATE_MONTAGE="${HOME}/my_work/gvmm/templates/Montage/"
TEMPLATE_SINGLE="${HOME}/my_work/gvmm/templates/Single/"

otl_mindmap="mindmap-01.otl"
montage="montage.gmm"
wiki="Template.wiki"
makefile="Makefile"
let scale=0
let creates=0
let createm=0


usage()
{
  printf "Usage: %s [argument]\n" $(basename $0) >&2
  printf "       [-s]                                  - create single mindmap from templates\n" >&2
  printf "       [-m]                                  - create montage from templates\n" >&2
  printf "       [-p]                                  - filename of otl mindmap (mindmap-01.otl)\n" >&2
  printf "       [-g]                                  - filename of montage (montage.gmm)\n" >&2
  printf "       [-w]                                  - filename of vimwiki (Template.wiki)\n" >&2
  printf "       [-f]                                  - filename of Makefile (Makefile)\n" >&2
  printf "       [-l]                                  - scale final montage (60%%)\n" >&2
  printf "       [-h]                                  - usage\n" >&2
  exit 2
}

if [[ $# == 0 ]]
then
    usage
fi

while getopts 'hsmp:g:w:f:l:' OPTION
do
    case $OPTION in
        s)
            creates=1
            ;;
        m)
            createm=1
            ;;
        g)
            montage="$OPTARG"
            ;;
        p)
            otl_mindmap="$OPTARG"
            ;;
        w)
            wiki="$OPTARG"
            ;;
        f)
            makefile="$OPTARG"
            ;;
        l)
            scale="$OPTARG"
            ;;
        h)
            usage
            ;;
        ?)
            usage
            ;;
    esac
done


if [ "${creates}" -gt 0 ]
then
  echo "Creating single otl mindmap..."

  echo cp "${TEMPLATE_SINGLE}"mindmap-01.otl ./"${otl_mindmap}"
  cp "${TEMPLATE_SINGLE}"mindmap-01.otl ./"${otl_mindmap}"

  echo sed -i -r "s/mindmap-01/${otl_mindmap%%.*}/g" ./"${otl_mindmap}"
  sed -i -r "s/mindmap-01/${otl_mindmap%%.*}/g" ./"${otl_mindmap}"

	if [[ "x${makefile}" != "xMakefile" ]]
	then
		echo cp "${TEMPLATE_SINGLE}"Makefile ./"${makefile}"
		cp "${TEMPLATE_SINGLE}"Makefile ./"${makefile}"
		sed -i -r "s/mindmap-01/${otl_mindmap%%.*}/g" ./"${makefile}"
	elif [[ "x${makefile}" == "xMakefile" ]]
	then
		echo -e "\nAdd target in Makefile\nmm1 = ${otl_mindmap}"
		echo -e "\$(mm1): step-\$(mm1) step-\$(montage1)"
		echo -e "step-\$(mm1):\n\tgvmm.py -f \$(mm1) > /dev/null"
	fi

	if [[ "x${wiki}" != "xTemplate.wiki" ]]
	then
		echo cp "${TEMPLATE_SINGLE}"Template.wiki ./"${wiki}"
		cp "${TEMPLATE_SINGLE}"Template.wiki ./"${wiki}"
		echo sed -i -r "s/mindmap-01/${otl_mindmap%%.*}/g" ./"${wiki}"
		sed -i -r "s/mindmap-01/${otl_mindmap%%.*}/g" ./"${wiki}"
		echo sed -i -r "s/Template.wiki/${wiki}/g" ./"${makefile}"
		sed -i -r "s/Template.wiki/${wiki}/g" ./"${makefile}"
	fi
fi

if [ "${createm}" -gt 0 ]
then
  echo "Creating montage otl mindmaps..."

  echo cp "${TEMPLATE_MONTAGE}"mindmap-01.otl ./"${otl_mindmap}"
  cp "${TEMPLATE_MONTAGE}"mindmap-01.otl ./"${otl_mindmap}"

  echo sed -i -r "s/mindmap-01/${otl_mindmap%%.*}/" ./"${otl_mindmap}"
  sed -i -r "s/mindmap-01/${otl_mindmap%%.*}/g" ./"${otl_mindmap}"

  echo cp "${TEMPLATE_MONTAGE}"Makefile ./"${makefile}"
  cp "${TEMPLATE_MONTAGE}"Makefile ./"${makefile}"
  echo sed -i -r "s/mindmap-01/${otl_mindmap%%.*}/g" ./"${makefile}"
  sed -i -r "s/mindmap-01/${otl_mindmap%%.*}/g" ./"${makefile}"

  echo cp "${TEMPLATE_MONTAGE}"Template.wiki ./"${wiki}"
  cp "${TEMPLATE_MONTAGE}"Template.wiki ./"${wiki}"
  echo sed -i -r "s/mindmap-01/${otl_mindmap%%.*}/g" ./"${wiki}"
  sed -i -r "s/mindmap-01/${otl_mindmap%%.*}/g" ./"${wiki}"
  echo sed -i -r "s/Template.wiki/${wiki}/g" ./"${makefile}"
  sed -i -r "s/Template.wiki/${wiki}/g" ./"${makefile}"

  echo cp "${TEMPLATE_MONTAGE}"montage.gmm ./"${montage}"
  cp "${TEMPLATE_MONTAGE}"montage.gmm ./"${montage}"
  echo sed -i -r "s/mindmap-01/${otl_mindmap%%.*}/g" ./"${montage}"
  sed -i -r "s/mindmap-01/${otl_mindmap%%.*}/g" ./"${montage}"
  echo sed -i -r "s/montage.gmm/${montage}/g" ./"${makefile}"
  sed -i -r "s/montage.gmm/${montage}/g" ./"${makefile}"

  if [ "${scale}" -gt 0 ]
  then
    echo sed -i -r "s/s 60/s ${scale}/g" ./"${makefile}"
    sed -i -r "s/s 60/s ${scale}/g" ./"${makefile}"
  fi

fi
