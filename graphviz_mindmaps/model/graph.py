def BuildNodeRefs(rootnodename, nodelevel, level):
    fromnode = rootnodename
    for index in range(0, level - 1):
        fromnode += "%s" % ("{:=02}".format(nodelevel[index] - 1))

    tonode = fromnode + "%s" % ("{:=02}".format(nodelevel[level - 1]))
    tabs = "\t" * (level + 1)
    return fromnode, tonode, tabs


def AppendNodeEdge(edge, tabs, fromnode, tonode, ntype, edgeattrs, edgetype):
    if ntype in edgetype and not edgeattrs:
        edge.append("%s%s:e -> %s:w[%s];\n" % (tabs, fromnode, tonode, edgetype[ntype]))
    elif edgeattrs:
        edge.append("%s%s:e -> %s:w[%s];\n" % (tabs, fromnode, tonode, edgeattrs))
    else:
        edge.append("%s%s:e -> %s:w;\n" % (tabs, fromnode, tonode))


def EmitTreeNodes(tree, nodetype, fontsize):
    chunks = []

    for node in tree.postorder():
        ntype = node.getype()
        if ntype == "root":
            continue

        if not node.is_leaf():
            if ntype in {"cred", "cgreen", "ccyan", "cblue", "cpink", "cyello", "corang", "cblack", "cgrey"}:
                rendered = node.element().replace(
                    "shape=box",
                    "margin=\"0.2,0.3\" shape=box fontsize=\"%s\"" % (fontsize["l"]) + "\n",
                )
                chunks.append(rendered)
            else:
                rendered = node.element().replace(nodetype["def"], nodetype["node"]) + "\n"
                if ntype not in ["img", "imgil"]:
                    rendered = rendered.replace("shape=box", "shape=box margin=\"0.2,0.2\"")
                chunks.append(rendered)
        else:
            chunks.append(node.element() + "\n")

    return "".join(chunks)


def FinalizeEdges(edge, arrlines, arrend):
    finalized = list(edge)
    for arrline in arrlines:
        arrline[1].append(arrend[arrline[0]])
        finalized.append(
            "%s -> %s %s;\n"
            % (
                arrline[1][0],
                arrline[1][1],
                arrline[2].replace(
                    "[",
                    "[ltail=\"%s\" lhead=\"%s\" "
                    % (arrline[1][0].replace("node", "cluster"), arrline[1][1].replace("node", "cluster")),
                ),
            )
        )
    return list(reversed(finalized))
