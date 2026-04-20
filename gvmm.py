#!/home/daniel/.pyenv/versions/gvmm-py3/bin/python3

import sys, re, subprocess, argparse, os, fontawesome, tempfile
from graphviz_mindmaps.constants import DEFAULT_BGCOLOR
from graphviz_mindmaps.execute.image import (
    ScaleImg as PackageScaleImg,
    WriteDot as PackageWriteDot,
    WriteImg as PackageWriteImg,
)
from graphviz_mindmaps.execute.montage import (
    CheckCM as PackageCheckCM,
    WriteMontage as PackageWriteMontage,
)
from graphviz_mindmaps.execute.restart import SendRestartMSG as PackageSendRestartMSG
from graphviz_mindmaps.model.document import RenderRuntime, RenderSession
from graphviz_mindmaps.parser.outline import (
    ExtractMindmapBlocks,
    ParseFnameLine as ParseFnameLineDetails,
)
from graphviz_mindmaps.render.dot import GenDot as PackageGenDot
from graphviz_mindmaps.render.label_html import (
    ApplyInlineBacktickBold,
)

gvroot = "/home/daniel/my_notes/"
dotbuf = ""
tmpdir = []
title = ""
montagetitle = None
notitle = False
bgcolor = DEFAULT_BGCOLOR

cfg = os.environ['HOME'] + "/.galapix/galapix.cfg"

class ArgHolder(object):
    pass

def WriteDot(DotFile):
    PackageWriteDot(dotbuf, DotFile)


def SendRestartMSG(sockwildcard, sockcfg=None):
    PackageSendRestartMSG(cfg, sockwildcard, sockcfg)


def ScaleImg(argholder):
    PackageScaleImg(argholder, gvroot)


def WriteImg(argholder):
    global gvroot
    global dotbuf
    global tmpdir
    global notitle
    result = PackageWriteImg(dotbuf, argholder, gvroot, title, notitle, tmpdir)
    gvroot = result["gvroot"]
    dotbuf = result["dotbuf"]
    tmpdir = result["tmpdir"]
    notitle = result["notitle"]


def CheckCM(img):
    return PackageCheckCM(img)


def WriteMontage(argholder):
    global gvroot
    global montagetitle
    PackageWriteMontage(argholder, gvroot, SendRestartMSG)


def ParseFnameLine(keyword, line):
    global notitle
    fname, should_hide_title = ParseFnameLineDetails(keyword, line)
    if should_hide_title:
        notitle = True
    return fname

def GenDot(lines, argholder, parser):
    global dotbuf, title, notitle, montagetitle, bgcolor, tmpdir, gvroot
    result = PackageGenDot(
        lines,
        argholder,
        RenderSession(
            dotbuf=dotbuf,
            title=title,
            notitle=notitle,
            bgcolor=bgcolor,
            tmpdir=tmpdir,
            gvroot=gvroot,
        ),
        RenderRuntime(
            fontawesome_symb=fontawesome.symb,
            tempfile_module=tempfile,
            subprocess_module=subprocess,
            parse_fname_line=ParseFnameLine,
            write_dot=lambda dotfile, current_dotbuf: PackageWriteDot(current_dotbuf, dotfile),
            write_img=lambda current_argholder, current_dotbuf, current_title, current_notitle, current_tmpdir, current_gvroot: PackageWriteImg(current_dotbuf, current_argholder, current_gvroot, current_title, current_notitle, current_tmpdir),
            write_montage=lambda current_argholder, current_gvroot, send_restart: PackageWriteMontage(current_argholder, current_gvroot, send_restart),
            send_restart_msg=SendRestartMSG,
        ),
    )
    dotbuf = result.dotbuf
    title = result.title
    notitle = result.notitle
    bgcolor = result.bgcolor
    tmpdir = result.tmpdir
    gvroot = result.gvroot


def main():
    argholder = ArgHolder()

    linesall = []

    parser = argparse.ArgumentParser()
    parser.add_argument('-r', dest='sock', nargs='+')
    parser.add_argument('-f', dest='files', nargs='+', help='mindmap outliner files')
    parser.add_argument('-m', '--mtg', action='store_true', help='build montage with montage.py')
    parser.add_argument('-p', dest='preview', action='store_true', help='preview with galaview.sh')
    parser.add_argument('-s', dest='scale', nargs='?', const="specified", help='scale image for specified percentage')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', dest='dotname', nargs='?', const="specified", help='generate .dot file instead of image')
    group.add_argument('-i', dest='jpgname', nargs='?', const="specified", help='override image filename')
    parser.parse_args(namespace=argholder)

    if argholder.files:
        for fil in argholder.files:
            fo = open(fil)
            for line in fo:
                linesall.append(line.rstrip())
    else:
        linesall = sys.stdin.read().splitlines()

    for linesbymm in ExtractMindmapBlocks(linesall, ApplyInlineBacktickBold):
        GenDot(linesbymm, argholder, parser)

main()
