#!/home/daniel/.pyenv/versions/vrdel-apps-py27/bin/python

import sys, os, subprocess, multiprocessing
import shutil, tempfile, re, fnmatch
import argparse

mini = False
curdir = None
notitle = False


class ArgHolder(object):
    pass

argholder = None


def callmontage(imgs, tile, tmpdir, name, row=None):
    skip = False

    os.chdir(curdir)

    if mini and not notitle:
        background = "#efefef"
    else:
        background = "#a0a0a0"

    if row == None:
        if len(imgs) == 1:
            if name == "mimg":
                imgs[0] = imgs[0].replace("img", "mimg")
            shutil.copy(imgs[0], "%s/%s" % (os.path.abspath("."), name))
            skip = True
        else:
            exestring = "gm montage -monitor -background '%s' -geometry +0+0 -tile %dx %s '%s/%s'" % (background, tile, ' '.join(imgs), tmpdir, name)
    else:
        if len(imgs) == 1:
            if "mimg" not in imgs[0]:
                os.symlink("%s/%s" % (os.path.abspath("."), imgs[0]), "%s/%s%d.jpg" % (tmpdir, name, row))
            else:
                os.symlink("%s" % (imgs[0]), "%s/%s%d.jpg" % (tmpdir, name, row))
            skip = True
        else:
            exestring = "gm montage -monitor -background '%s' -geometry +0+0 -tile %dx %s %s/%s%d.jpg" % (background, tile, ' '.join(imgs), tmpdir, name, row)

    if not skip:
        subprocess.call(exestring, shell=True)


def SingleMontage(l, nummini = None):
    global curdir

    limg = []
    m = re.search("(\s*\+?\s*(?:(?:auto)|(?:[\w_\-\+\d]*\.(?:jpg|png))))\s*\{(?:\s*<EMPTYL>|\[newrow\]|\[nr\])?\s*(title\s*=\s*(?:(?:auto)|(?:[\"\'].*?[\"\'])))?(?:\s*<EMPTYL>|\[newrow\]|\[nr\])?\s*(size\s*=\s*(?:[\"\']?[smb][\"\']?))?\s*(.*[\w_\-\+\d]*.(jpg|png)\s*\+?.*){1,}\}", l)
    if argholder.outfile:
        orgfilename = filename = argholder.outfile
    else:
        orgfilename = filename = m.group(1).strip()
    if "+" in filename:
        filename = re.findall("(?:\s*\+?\s*((?:auto)|(?:[\w_\-\+\d]*\.(?:jpg|png))))", filename)
        if filename:
            filename = filename[0]
    if filename == "auto":
        if not mini:
            t = curdir.split("/")
            l = t[len(t) - 1]
            cml = len(argholder.cmfile)
            tind = cml - argholder.cmfile.rfind('.')
            filename = l + "_" + argholder.cmfile[:-tind] + ".jpg"
        elif mini and nummini:
            cml = len(argholder.cmfile)
            tind = cml - argholder.cmfile.rfind('.')
            filename = argholder.cmfile[:-tind] + "-m%i" % (nummini) + ".jpg"
        orgfilename = orgfilename.split("auto")[0] + filename
    if m.group(2):
        title = m.group(2)
        tl = title.split("=")
        title = re.findall("[\"\'](.*)[\"\']", tl[1])
        if title:
            title = title[0]
        else:
            title = tl[1].strip()
        if title == "auto":
            title = filename
    else:
        global notitle
        notitle = True
        title = None
    if m.group(3):
        size = m.group(3)
        tl = size.split("=")
        size = re.findall("[\"\']?([smb])[\"\']?", tl[1])[0]
    else:
        if mini:
            size = 's'
        else:
            size = 'm'
    t = m.group(4)
    m = re.findall("(([\w\-_\d]*\.(?:jpg|png)(?:\s*\+\s*[\w\-_\d]*.(?:jpg|png))*)|(<EMPTYL>|\[newrow\]|\[nr\]))", t)
    if "<EMPTYL>" in m[0] or "[newrow]" in m[0] or '[nr]' in m[0]:
        del(m[0])
    for i in m:
        limg.append(i[0].strip())

    CreateMontage(filename, title, size, limg)

    notitle = False
    return orgfilename


def MultiMontage(l):
    minifilenames = []
    global mini, title, notitle

    m = re.match("((?:auto)|(?:[\w_\-\d]*\.(?:jpg|png)))\s*\{\s*(title\s*=\s*(?:(?:auto)|(?:\".*?\")))?\s*(size\s*=\s*[smb])?\s*(.*)\s*\}", l)
    filename = m.group(1)
    if m.group(2):
        title = m.group(2)
        tl = title.split("=")
        title = re.findall("\"(.*)\"", tl[1])
        if title:
            title = title[0]
        else:
            title = tl[1].strip()
    else:
        title = None
    if m.group(3):
        size = m.group(3)
        tl = size.split("=")
        size = tl[1].strip()
    else:
        size = None
    t = m.group(4)
    m = re.findall("((?:(?:\+?\s*auto)|(?:\+?[\s\w_\-\d]*\.(?:jpg|png)))\s*\{.*?\})|(<EMPTYL>|\[newrow\]|\[nr\])|((?:\s*\+?\s*[\w\-_\d]*\.(?:jpg|png)(?:\s*\+\s*[\w\-_\d]*.(?:jpg|png))*))", t)
    j, k = 1, 1
    for i in m:
        if i[0]:
            if i[0].strip().startswith("+"):
                if re.match(".*?-m[0-9]+\.", minifilenames[-1]):
                    left = minifilenames[-1]
                    del(minifilenames[-1])
                else:
                    cml = len(argholder.cmfile)
                    tind = cml - argholder.cmfile.rfind('.')
                    arg = "%s-m%i.jpg { " % (argholder.cmfile[:-tind], j)
                    arg += " ".join(minifilenames) + " }"
                    del(minifilenames[:])
                    mini = False
                    left = SingleMontage(arg, j)
                    j += 1
            else:
                left = ""
            mini = True
            minifilenames.append(left + SingleMontage(i[0].strip(), j))
            j += 1
        elif i[1]:
            minifilenames.append(i[1].strip())
        elif i[2]:
            if i[2].strip().startswith("+"):
                if re.match(".*?-m[0-9]+\.", minifilenames[-1]):
                    minifilenames[-1] = minifilenames[-1] + i[2].strip()
                else:
                    cml = len(argholder.cmfile)
                    tind = cml - argholder.cmfile.rfind('.')
                    arg = "%s-m%i.jpg { " % (argholder.cmfile[:-tind], j)
                    arg += " ".join(minifilenames) + " }"
                    del(minifilenames[:])
                    mini = False
                    minifilenames.append(SingleMontage(arg, j) + i[2].strip())
                    j += 1
            else:
                minifilenames.append(i[2].strip())


    arg = "%s { " % filename
    if title:
        arg += "title = \"%s\" " % title
    if size:
        arg += "size = %s " % size

    arg += " ".join(minifilenames) + " }"

    mini = False
    SingleMontage(arg)


def CreateMontage(filename, title, size, limg):
    os.chdir(curdir)

    imgnames = []
    rowimgs = []
    multimgnames = []
    tmpfiles = []
    row = 0
    multimg = 0
    tmpdir = tempfile.mkdtemp()

    for line in limg:
        if line.find("+") > 0:
            multimg += 1
            multimgnames = line.split("+")
            for i in range(len(multimgnames)):
                multimgnames[i] = multimgnames[i].strip()
            m = multiprocessing.Process(name = 'callmontage', target = callmontage, args = (multimgnames, 1, tmpdir, "mimg", multimg))
            m.start()
            m.join()
            imgnames.append("%s/mimg%d.jpg" % (tmpdir, multimg))
            tmpfiles.append("%s/mimg%d.jpg" % (tmpdir, multimg))
        elif "<EMPTYL>" in line or '[newrow]' in line or '[nr]' in line:
            row += 1
            m = multiprocessing.Process(name = 'callmontage', target = callmontage, args = (imgnames, len(imgnames), tmpdir, "img", row))
            m.start()
            m.join()
            imgnames = []
            rowimgs.append("%s/img%d.jpg" % (tmpdir, row))
            tmpfiles.append("%s/img%d.jpg" % (tmpdir, row))
        else:
            imgnames.append(line)
    else:
        row += 1
        m = multiprocessing.Process(name = 'callmontage', target = callmontage, args = (imgnames, len(imgnames), tmpdir, "img", row))
        m.start()
        m.join()
        rowimgs.append("%s/img%d.jpg" % (tmpdir, row))
        tmpfiles.append("%s/img%d.jpg" % (tmpdir, row))

    m = multiprocessing.Process(name = 'callmontage', target = callmontage, args = (rowimgs, 1, ".", filename.strip()))
    m.start()
    m.join()

    if title:
        subprocess.call("montit.py -s '%s' -t '%s' '%s'" % (size, title, filename), shell = True)

    if argholder.scale and not mini:
        cmd = "gm convert -scale %s%% '%s' '%s'" % (argholder.scale, filename, filename)
        subprocess.call(cmd, shell=True)

    os.chdir(tmpdir)
    for i in tmpfiles:
        os.remove(i)
    os.removedirs(tmpdir)


def main():
    global curdir
    global mini
    global argholder

    argholder = ArgHolder()
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', dest='scale', nargs='?', const="specified")
    parser.add_argument('-o', dest='outfile', type=str, required=False, default="")
    parser.add_argument('cmfile')
    parser.parse_args(namespace=argholder)

    curdir = os.path.abspath(".")
    f = open(argholder.cmfile)
    lines = f.readlines()
    buf = "\t".join(lines)
    buf = re.sub("\t\n", "<EMPTYL>", buf)
    buf = buf.replace("\n", "")
    f.close()

    m = re.search("\{.*\{.*\}.*\}", buf)

    if m:
        mini = True
        MultiMontage(buf)
    else:
        SingleMontage(buf)

main()
