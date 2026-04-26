import os, sys, argparse, subprocess, math
from PIL import Image, ImageDraw, ImageFont, ImageOps

Image.MAX_IMAGE_PIXELS = None
DEFAULT_BACKGROUND = "#4b5262"
TITLE_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"
FRAME_FILL = "#5d6576"
TITLE_FILL = "black"
SIDE_MARGIN = 15
TOP_MARGIN = 10
BOTTOM_OVERLAP = 15
FRAME_BORDER = 5


def Montage(argholder):
    if argholder.EmptyImg != "NoSpec":
        i = 1
        while i <= len(argholder.files) - 1:
            argholder.files.insert(i, argholder.EmptyImg)
            i += 2
        argholder.MontageTile = argholder.MontageTile * 2

    exe = "gm montage -monitor -background '%s' -geometry +0+0 -tile \"%sx\" \"%s\" \"%s\"" \
            % (argholder.Background, argholder.MontageTile, '" "'.join(argholder.files[:-1]), \
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

    with Image.open(InImg) as image:
        im = image.convert("RGB")

    # PointSize = math.floor(TitleFrac[argholder.TitleSize] * im.size[1])
    # SpliceSize = math.floor(PointSize + SpliceFrac[argholder.TitleSize])


    PointSize = TitleFrac[argholder.TitleSize]
    SpliceSize = PointSize + SpliceFrac[argholder.TitleSize]

    # exe = "convert \"%s\" -monitor -bordercolor black -border 4 -font DejaVu-Sans-Condensed-Bold -pointsize %d -fill white -gravity North -background black -splice 0x%d -bordercolor '#a0a0a0' -border 10 -annotate +5+20 '%s' \"%s\"" % (InImg, PointSize, SpliceSize, argholder.ImgTitle, OutImg)

    frame_border = FRAME_BORDER
    frame_fill = FRAME_FILL
    title_fill = TITLE_FILL
    side_margin = SIDE_MARGIN
    top_margin = TOP_MARGIN
    bottom_overlap = BOTTOM_OVERLAP
    canvas_width = im.size[0] + (side_margin * 2)
    canvas_height = im.size[1] + SpliceSize
    image_x = side_margin
    image_y = SpliceSize - bottom_overlap

    framed = ImageOps.expand(im, border=frame_border, fill=frame_fill)
    canvas = Image.new("RGB", (canvas_width, canvas_height), argholder.Background)
    canvas.paste(framed, (image_x - frame_border, image_y - frame_border))

    draw = ImageDraw.Draw(canvas)
    title_rect = (top_margin, top_margin, canvas_width - top_margin - 1, SpliceSize - bottom_overlap)
    draw.rectangle(title_rect, fill=title_fill)

    font = ImageFont.truetype(TITLE_FONT, PointSize)
    text_bbox = draw.textbbox((0, 0), argholder.ImgTitle, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = title_rect[0] + max(0, ((title_rect[2] - title_rect[0]) - text_width) // 2) - text_bbox[0]
    text_y = title_rect[1] + max(0, ((title_rect[3] - title_rect[1]) - text_height) // 2) - text_bbox[1]
    draw.text((text_x, text_y), argholder.ImgTitle, font=font, fill="white")

    canvas.save(OutImg)

def main():
    class ArgHolder(object):
        pass

    argholder = ArgHolder()

    parser = argparse.ArgumentParser()
    parser.add_argument('-t', dest = 'ImgTitle', nargs = '?', default = "NoSpec")
    parser.add_argument('-s', dest = 'TitleSize', choices = ['xs', 's', 'm', 'b'], default = 's')
    parser.add_argument('-e', dest = 'EmptyImg', nargs = '?', default = "NoSpec")
    parser.add_argument('-m', dest = 'MontageTile', type = int)
    parser.add_argument('-b', '--background', dest='Background', default=DEFAULT_BACKGROUND)
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

if __name__ == "__main__":
    main()
