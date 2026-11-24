import os
import shutil
import subprocess
import tempfile

from PIL import Image

from graphviz_mindmaps.tools.montage_title import title_canvas

Image.MAX_IMAGE_PIXELS = None
DEFAULT_PNG_COMPRESSION = 1
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


def ParsePngCompression(value):
    value = str(value).strip()
    if not value.isascii() or not value.isdecimal() or not 0 <= int(value) <= 9:
        raise ValueError('png_compression must be an integer from 0 to 9')
    return int(value)


def PostProcessImage(source, output, title, notitle=False, scale=None,
                     png_compression=DEFAULT_PNG_COMPRESSION):
    """Crop, title, and scale in memory, then atomically encode only once."""
    png_compression = ParsePngCompression(png_compression)
    with Image.open(source) as image:
        left = min(2, image.width // 2)
        top = min(2, image.height // 2)
        right = max(left + 1, image.width - left)
        bottom = max(top + 1, image.height - top)
        result = image.crop((left, top, right, bottom))
    pending = None
    try:
        if not notitle:
            framed = title_canvas(result, title, size='s')
            result.close()
            result = framed
        if scale:
            percent = int(scale)
            width = max(1, round(result.width * percent / 100))
            height = max(1, round(result.height * percent / 100))
            resized = result.resize((width, height), Image.Resampling.LANCZOS)
            result.close()
            result = resized
        suffix = os.path.splitext(output)[1].lower()
        if suffix in {'.jpg', '.jpeg'} and result.mode not in {'RGB', 'L', 'CMYK'}:
            converted = result.convert('RGB')
            result.close()
            result = converted
        descriptor, pending = tempfile.mkstemp(prefix='.gvmm-output-', suffix=suffix,
                                                dir=os.path.dirname(os.path.abspath(output)))
        os.close(descriptor)
        options = {'compress_level': png_compression} if suffix == '.png' else {}
        result.save(pending, **options)
        os.replace(pending, output)
    finally:
        result.close()
        if pending is not None and os.path.exists(pending):
            os.unlink(pending)


def WriteImg(dotbuf, argholder, gvroot, title, notitle, tmpdir,
             png_compression=DEFAULT_PNG_COMPRESSION):
    png_compression = ParsePngCompression(png_compression)
    gvroot, argholder.jpgname = ResolveOutputRoot(gvroot, argholder.jpgname)
    output = gvroot + argholder.jpgname
    temp_root = tempfile.mkdtemp(prefix='gvmm-render-')
    tmpdir.append(temp_root)
    raw = os.path.join(temp_root, 'graph.' + _output_format_for_path(output))
    try:
        RenderDotImage(dotbuf, raw, tmpdir)
        PostProcessImage(raw, output, title, notitle, argholder.scale, png_compression)
    finally:
        tmpdir = CleanupTmpdir(tmpdir)

    if argholder.preview:
        subprocess.Popen(['galaview.sh', output])
    argholder.jpgname = None
    return {'gvroot': gvroot, 'dotbuf': '', 'tmpdir': tmpdir, 'notitle': False}
