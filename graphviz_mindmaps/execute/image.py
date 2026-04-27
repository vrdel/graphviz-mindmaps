import os
import subprocess
import sys

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
MONTAGE_TITLE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "montage_title.py")


def WriteDot(dotbuf, dotfile):
    outputfile = open(dotfile, "w")
    outputfile.write(dotbuf)
    outputfile.close()


def ResizeByPercent(path, scale_percent):
    with Image.open(path) as image:
        width = max(1, round(image.width * scale_percent / 100))
        height = max(1, round(image.height * scale_percent / 100))
        resized = image.resize((width, height), Image.Resampling.LANCZOS)
        resized.save(path)


def ShaveImage(path, shave_x=2, shave_y=2):
    with Image.open(path) as image:
        left = min(shave_x, image.width // 2)
        top = min(shave_y, image.height // 2)
        right = max(left + 1, image.width - left)
        bottom = max(top + 1, image.height - top)
        shaved = image.crop((left, top, right, bottom))
        shaved.save(path)


def ScaleImg(argholder, gvroot):
    ResizeByPercent(gvroot + argholder.jpgname, int(argholder.scale))


def ResolveOutputRoot(gvroot, jpgname, environ=None):
    if environ is None:
        environ = os.environ

    if jpgname.startswith("~") or jpgname.startswith("/"):
        return "", jpgname.replace("~", environ["HOME"])
    if "/" not in jpgname and "~" not in jpgname:
        return environ["PWD"] + "/", jpgname
    return gvroot, jpgname


def CleanupTmpdir(tmpdir):
    if len(tmpdir) > 0:
        for path in tmpdir:
            os.remove("%s/doodle.png" % (path))
            os.removedirs(path)
    return []


def WriteImg(dotbuf, argholder, gvroot, title, notitle, tmpdir):
    gvroot, argholder.jpgname = ResolveOutputRoot(gvroot, argholder.jpgname)

    proc = subprocess.Popen(["dot", "-Tjpg", "-o", gvroot + argholder.jpgname], stdin=subprocess.PIPE)
    proc.communicate(dotbuf.encode())

    ShaveImage(gvroot + argholder.jpgname, shave_x=2, shave_y=2)

    if not notitle:
        subprocess.call(
            [sys.executable, MONTAGE_TITLE_PATH, "-s", "s", "-t", title, gvroot + argholder.jpgname]
        )

    if argholder.scale:
        ScaleImg(argholder, gvroot)

    if argholder.preview:
        subprocess.call(
            "FvwmCommand 'All (galapix:*%s*) Close'"
            % argholder.jpgname.split("/")[1]
            if "/" in argholder.jpgname
            else argholder.jpgname,
            shell=True,
        )
        subprocess.Popen(["galaview.sh", gvroot + argholder.jpgname])

    tmpdir = CleanupTmpdir(tmpdir)

    next_dotbuf = ""
    next_notitle = False
    argholder.jpgname = None

    return {
        "gvroot": gvroot,
        "dotbuf": next_dotbuf,
        "tmpdir": tmpdir,
        "notitle": next_notitle,
    }
