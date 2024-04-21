mm1 = mindmap-01.otl
montage1 = montage.gmm
wiki1 = Template.wiki

step-$(montage1):
	montage.py -s 60 $(montage1) > /dev/null
	vim -c ':Vimwiki2HTML' -c ':wq' '$(wiki1)' > /dev/null
	galacomm.py -r vimwiki_mindmaps > /dev/null || galaview.sh "`basename \"${PWD}\"`_`basename \"$(montage1)\" .gmm`".* &

step-$(mm1):
	gvmm.py -f $(mm1) > /dev/null

$(mm1): step-$(mm1) step-$(montage1)

.PHONY: $(mm1)
