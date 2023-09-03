#!/home/daniel/.pyenv/versions/vrdel-apps-py27/bin/python

import os, sys, argparse, subprocess, math
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def Montage(argholder):
    if argholder.EmptyImg != "NoSpec":
        i = 1
        while i <= len(argholder.files) - 1:
            argholder.files.insert(i, argholder.EmptyImg)
            i += 2
        argholder.MontageTile = argholder.MontageTile * 2

    exe = "gm montage -monitor -background white -geometry +0+0 -tile \"%sx\" \"%s\" \"%s\"" \
            % (argholder.MontageTile, '" "'.join(argholder.files[:-1]), \
            argholder.files[len(argholder.files) - 1])

    subprocess.call(exe, shell = True)

def TitleImg(argholder):
    InImg = ""
    OutImg = ""
    SpliceFrac = {'xs': 30, 's' : 50, 'm' : 70, 'b' : 100}
    TitleFrac = {'xs': 35, 's' : 80, 'm' : 148, 'b' : 232}

    if not argholder.MontageTile:
        if len(argholder.files) == 2:
            InImg = argholder.files[0]
            OutImg = argholder.files[1]
        elif len(argholder.files) == 1:
            InImg = OutImg = argholder.files[0]
        elif len(argholder.files) == 0:
            InImg = OutImg = argholder.ImgTitle
    else:
        InImg = OutImg = argholder.files[len(argholder.files) - 1]

    im = Image.open(InImg)

    # PointSize = math.floor(TitleFrac[argholder.TitleSize] * im.size[1])
    # SpliceSize = math.floor(PointSize + SpliceFrac[argholder.TitleSize])


    PointSize = TitleFrac[argholder.TitleSize]
    SpliceSize = PointSize + SpliceFrac[argholder.TitleSize]

    # exe = "convert \"%s\" -monitor -bordercolor black -border 4 -font DejaVu-Sans-Condensed-Bold -pointsize %d -fill white -gravity North -background black -splice 0x%d -bordercolor '#a0a0a0' -border 10 -annotate +5+20 '%s' \"%s\"" % (InImg, PointSize, SpliceSize, argholder.ImgTitle, OutImg)

    exe = "gm convert '%s' -mattecolor black -frame 5x5+0+0 -gravity south \
        -background '#a0a0a0' -extent %dx%d+0-15 -pointsize %d -draw 'rectangle 10,10 %i,%i' \
        -font /usr/share/fonts/dejavu/DejaVuSansCondensed-Bold.ttf -fill white -gravity north \
        -monitor -draw \"text 0,%d '%s'\" '%s'" % (InImg, im.size[0] + 30, im.size[1] + SpliceSize, \
                                        PointSize, im.size[0] + 20 - 1, SpliceSize - 15, PointSize + 7, \
                                        argholder.ImgTitle, OutImg)

    subprocess.call(exe, shell = True)

def main():
    class ArgHolder(object):
        pass

    argholder = ArgHolder()

    parser = argparse.ArgumentParser()
    parser.add_argument('-t', dest = 'ImgTitle', nargs = '?', default = "NoSpec")
    parser.add_argument('-s', dest = 'TitleSize', choices = ['xs', 's', 'm', 'b'], default = 's')
    parser.add_argument('-e', dest = 'EmptyImg', nargs = '?', default = "NoSpec")
    parser.add_argument('-m', dest = 'MontageTile', type = int)
    parser.add_argument('files', nargs = argparse.REMAINDER)

    parser.parse_args(namespace = argholder)


    if argholder.MontageTile:

        Montage(argholder)

        if argholder.ImgTitle != "NoSpec":
            if argholder.ImgTitle == None:
                if len(argholder.files) > 1:
                    argholder.ImgTitle = argholder.files[len(argholder.files) - 1]
                else:
                    argholder.ImgTitle = argholder.files[0]
            TitleImg(argholder)

    elif argholder.ImgTitle != "NoSpec":
        TitleImg(argholder)

main()
