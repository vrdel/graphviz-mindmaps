import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
MONTAGE_TITLE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "montage_title.py")
CAIRO_BITMAP_LIMIT_ERROR = "too large for cairo-renderer bitmaps"


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
            if os.path.isdir(path):
                shutil.rmtree(path)
    return []


def _format_command_error(command, result):
    stderr = result.stderr.decode(errors="replace") if result.stderr else ""
    stdout = result.stdout.decode(errors="replace") if result.stdout else ""
    message = stderr.strip() or stdout.strip() or "no output"
    return "%s failed with exit code %s: %s" % (" ".join(command), result.returncode, message)


def _render_dot(dotbuf, output_path, output_format):
    command = ["dot", "-T%s" % output_format, "-o", output_path]
    return subprocess.run(command, input=dotbuf.encode(), capture_output=True)


def _output_format_for_path(output_path):
    suffix = os.path.splitext(output_path)[1].lower()
    if suffix == ".png":
        return "png"
    return "jpg"


def _save_png_as_output(png_path, output_path):
    suffix = os.path.splitext(output_path)[1].lower()
    if suffix == ".png":
        shutil.copyfile(png_path, output_path)
        return

    with Image.open(png_path) as image:
        if suffix in {".jpg", ".jpeg"}:
            image.convert("RGB").save(output_path)
        else:
            image.save(output_path)


def _render_via_svg_fallback(dotbuf, output_path, tmpdir):
    converter = shutil.which("inkscape")
    if not converter:
        raise RuntimeError(
            "dot hit the cairo bitmap size limit and inkscape is not installed; "
            "install inkscape or render with -d to keep DOT output"
        )

    temp_root = tempfile.mkdtemp(prefix="gvmm-svg-fallback-")
    tmpdir.append(temp_root)
    svg_path = os.path.join(temp_root, "graph.svg")
    png_path = os.path.join(temp_root, "graph.png")

    svg_result = _render_dot(dotbuf, svg_path, "svg")
    if svg_result.returncode != 0:
        raise RuntimeError(_format_command_error(["dot", "-Tsvg", "-o", svg_path], svg_result))

    command = [converter, svg_path, "--export-type=png", "--export-filename", png_path]
    convert_result = subprocess.run(command, capture_output=True)
    if convert_result.returncode != 0:
        raise RuntimeError(_format_command_error(command, convert_result))

    _save_png_as_output(png_path, output_path)


def RenderDotImage(dotbuf, output_path, tmpdir):
    output_format = _output_format_for_path(output_path)
    result = _render_dot(dotbuf, output_path, output_format)
    stderr = result.stderr.decode(errors="replace") if result.stderr else ""
    if CAIRO_BITMAP_LIMIT_ERROR in stderr:
        _render_via_svg_fallback(dotbuf, output_path, tmpdir)
        return

    if result.returncode == 0:
        return

    raise RuntimeError(_format_command_error(["dot", "-T%s" % output_format, "-o", output_path], result))


def WriteImg(dotbuf, argholder, gvroot, title, notitle, tmpdir):
    gvroot, argholder.jpgname = ResolveOutputRoot(gvroot, argholder.jpgname)

    RenderDotImage(dotbuf, gvroot + argholder.jpgname, tmpdir)

    ShaveImage(gvroot + argholder.jpgname, shave_x=2, shave_y=2)

    if not notitle:
        subprocess.call(
            [sys.executable, MONTAGE_TITLE_PATH, "-s", "s", "-t", title, gvroot + argholder.jpgname]
        )

    if argholder.scale:
        ScaleImg(argholder, gvroot)

    if argholder.preview:
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
