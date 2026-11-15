import argparse
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
DEFAULT_BACKGROUND = "#a0a0a0"
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

def render_title(source, output, title, size='s', background=DEFAULT_BACKGROUND):
    """Add the existing frame/title without full-size RGB and border copies.

    PNGs are lossless working artifacts. Use fast compression rather than the
    default level 6; JPEG and other output encoders retain their defaults.
    """
    point_size = {'xs': 35, 's': 80, 'm': 148, 'b': 232}[size]
    splice = point_size + {'xs': 30, 's': 50, 'm': 70, 'b': 100}[size]
    image_x = SIDE_MARGIN
    image_y = splice - BOTTOM_OVERLAP

    with Image.open(source) as image:
        width, height = image.size
        canvas = Image.new('RGB', (width + SIDE_MARGIN * 2, height + splice), background)
        try:
            draw = ImageDraw.Draw(canvas)
            # Draw just the border directly on the destination. ImageOps.expand
            # would allocate a second full-size copy of the decoded source.
            draw.rectangle((image_x - FRAME_BORDER, image_y - FRAME_BORDER,
                            image_x + width + FRAME_BORDER - 1,
                            image_y + height + FRAME_BORDER - 1),
                           outline=FRAME_FILL, width=FRAME_BORDER)
            # Paste converts non-RGB modes as needed, without retaining a separate
            # RGB source copy. No mask: preserve the original alpha-flattening
            # behavior of image.convert('RGB').
            canvas.paste(image, (image_x, image_y))
        except BaseException:
            canvas.close()
            raise

    # The source is now closed, before text rendering and output compression.
    try:
        draw = ImageDraw.Draw(canvas)
        title_rect = (TOP_MARGIN, TOP_MARGIN, canvas.width - TOP_MARGIN - 1, image_y)
        draw.rectangle(title_rect, fill=TITLE_FILL)
        font = ImageFont.truetype(TITLE_FONT, point_size)
        text_bbox = draw.textbbox((0, 0), title, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        text_x = title_rect[0] + max(0, ((title_rect[2] - title_rect[0]) - text_width) // 2) - text_bbox[0]
        text_y = title_rect[1] + max(0, ((title_rect[3] - title_rect[1]) - text_height) // 2) - text_bbox[1]
        draw.text((text_x, text_y), title, font=font, fill='white')
        options = {'compress_level': 1} if Path(output).suffix.lower() == '.png' else {}
        canvas.save(output, **options)
    finally:
        canvas.close()


def TitleImg(argholder):
    if argholder.MontageTile:
        source = output = argholder.files[-1]
    elif len(argholder.files) == 2:
        source, output = argholder.files
    elif len(argholder.files) == 1:
        source = output = argholder.files[0]
    else:
        source = output = argholder.ImgTitle
    render_title(source, output, argholder.ImgTitle, argholder.TitleSize, argholder.Background)


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
