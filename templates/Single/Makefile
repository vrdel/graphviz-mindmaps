mm1 = mindmap-01.otl
wiki1 = Template.wiki

step-$(mm1):
	gvmm.py -s 60 -f $(mm1) &> /dev/null
	vim -c ':Vimwiki2HTML' -c ':wq' $(wiki1) &> /dev/null
	galacomm.py -r vimwiki_mindmaps &> /dev/null || galaview.sh `basename $(mm1) .otl`.[jp]*

$(mm1): step-$(mm1)

.PHONY: $(mm1)
