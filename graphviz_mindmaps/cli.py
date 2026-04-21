#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import tempfile

import fontawesome

from graphviz_mindmaps.constants import DEFAULT_BGCOLOR
from graphviz_mindmaps.execute.image import WriteDot, WriteImg
from graphviz_mindmaps.execute.montage import WriteMontage
from graphviz_mindmaps.execute.restart import SendRestartMSG
from graphviz_mindmaps.model.document import RenderRuntime, RenderSession
from graphviz_mindmaps.parser.outline import ExtractMindmapBlocks, ParseFnameLine
from graphviz_mindmaps.render.dot import GenDot
from graphviz_mindmaps.render.label_html import ApplyInlineBacktickBold


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", dest="sock", nargs="+")
    parser.add_argument("-f", dest="files", nargs="+", help="mindmap outliner files")
    parser.add_argument("-m", "--mtg", action="store_true", help="build montage with montage.py")
    parser.add_argument("-p", dest="preview", action="store_true", help="preview with galaview.sh")
    parser.add_argument("-s", dest="scale", nargs="?", const="specified", help="scale image for specified percentage")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-d", dest="dotname", nargs="?", const="specified", help="generate .dot file instead of image")
    group.add_argument("-i", dest="jpgname", nargs="?", const="specified", help="override image filename")
    return parser


def read_input_lines(files):
    linesall = []
    if files:
        for fil in files:
            with open(fil) as fo:
                for line in fo:
                    linesall.append(line.rstrip())
    else:
        linesall = sys.stdin.read().splitlines()
    return linesall


def build_runtime(session, cfg):
    def parse_fname_line(keyword, line):
        fname, should_hide_title = ParseFnameLine(keyword, line)
        if should_hide_title:
            session.notitle = True
        return fname

    def write_img(argholder, current_dotbuf, current_title, current_notitle, current_tmpdir, current_gvroot):
        result = WriteImg(current_dotbuf, argholder, current_gvroot, current_title, current_notitle, current_tmpdir)
        session.gvroot = result["gvroot"]
        session.dotbuf = result["dotbuf"]
        session.tmpdir = result["tmpdir"]
        session.notitle = result["notitle"]
        return result

    def write_montage(argholder, current_gvroot, send_restart):
        return WriteMontage(argholder, current_gvroot, send_restart)

    def send_restart_msg(sockwildcard, sockcfg=None):
        return SendRestartMSG(cfg, sockwildcard, sockcfg)

    return RenderRuntime(
        fontawesome_symb=fontawesome.symb,
        tempfile_module=tempfile,
        subprocess_module=subprocess,
        parse_fname_line=parse_fname_line,
        write_dot=lambda dotfile, current_dotbuf: WriteDot(current_dotbuf, dotfile),
        write_img=write_img,
        write_montage=write_montage,
        send_restart_msg=send_restart_msg,
    )


def main():
    parser = build_parser()
    argholder = parser.parse_args()

    session = RenderSession(
        dotbuf="",
        title="",
        notitle=False,
        bgcolor=DEFAULT_BGCOLOR,
        tmpdir=[],
        gvroot="/home/daniel/my_notes/",
    )
    cfg = os.environ["HOME"] + "/.galapix/galapix.cfg"
    runtime = build_runtime(session, cfg)

    linesall = read_input_lines(argholder.files)
    for linesbymm in ExtractMindmapBlocks(linesall, ApplyInlineBacktickBold):
        session = GenDot(linesbymm, argholder, session, runtime)


if __name__ == "__main__":
    main()
