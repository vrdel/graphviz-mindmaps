from pathlib import Path
import re

from PIL import Image, ImageColor, ImageFilter, ImageOps


IMAGE_TRANSFORM_KEY_PATTERN = (
    r"img(?:_neg)?(?:_gr)?(?:_cn)?(?:_sk)?"
    r"(?:_c(?:def|green|cyan|blue|pink|red|yello|orang|white)(?:[0-9]+)?)?"
)

_TRANSFORM_OPTIONS = {
    "neg": "negate",
    "gr": "grayscale",
    "cn": "contrast",
    "sk": "sketch",
}


def ParseImageTransformKey(key: str) -> dict[str, bool | str | float] | None:
    if not re.fullmatch(IMAGE_TRANSFORM_KEY_PATTERN, key):
        return None

    parts = key.split("_")[1:]
    options: dict[str, bool | str | float] = {}
    previous_index = -1
    for part in parts:
        color_match = re.fullmatch(
            r"(c(?:def|green|cyan|blue|pink|red|yello|orang|white))([0-9]+)?",
            part,
        )
        if color_match:
            options["overlay_token"] = color_match.group(1)
            if color_match.group(2) is not None:
                opacity_percent = int(color_match.group(2))
                if opacity_percent > 100:
                    return None
                options["overlay_opacity"] = opacity_percent / 100
            continue

        option_index = tuple(_TRANSFORM_OPTIONS).index(part)
        if option_index <= previous_index:
            return None
        previous_index = option_index
        options[_TRANSFORM_OPTIONS[part]] = True

    return options


def IsImageTransformKey(key: str) -> bool:
    return key != "img" and ParseImageTransformKey(key) is not None


def ParseImageTransformSpec(spec: str) -> tuple[str, float | None]:
    image, separator, scale = spec.rpartition("|")
    if not separator:
        return spec, None

    try:
        scale_percent = float(scale)
    except ValueError as exc:
        raise ValueError(f"invalid image scale percentage: {scale!r}") from exc
    if scale_percent <= 0:
        raise ValueError("image scale percentage must be greater than zero")
    return image, scale_percent


def TransformImage(
    source: str | Path,
    output: str | Path,
    negate: bool = False,
    grayscale: bool = False,
    contrast: bool = False,
    sketch: bool = False,
    overlay_color: str | None = None,
    overlay_opacity: float = 0.2,
    scale_percent: float | None = None,
) -> None:
    source = Path(source)
    output = Path(output)

    with Image.open(source) as image:
        has_alpha = "A" in image.getbands() or "transparency" in image.info
        rgba = image.convert("RGBA") if has_alpha else None
        alpha = rgba.getchannel("A") if rgba else None
        transformed = rgba.convert("RGB") if rgba else image.convert("RGB")

        if negate:
            transformed = ImageOps.invert(transformed)
        if grayscale or sketch:
            transformed = ImageOps.grayscale(transformed)
        if contrast:
            transformed = ImageOps.autocontrast(transformed, cutoff=2)
        if sketch:
            transformed = transformed.filter(ImageFilter.CONTOUR)
        if overlay_color is not None:
            if not 0 <= overlay_opacity <= 1:
                raise ValueError("image overlay opacity must be between zero and one")
            transformed = transformed.convert("RGB")
            overlay = Image.new("RGB", transformed.size, ImageColor.getrgb(overlay_color))
            transformed = Image.blend(transformed, overlay, overlay_opacity)

        if scale_percent is not None:
            width = max(1, round(transformed.width * scale_percent / 100))
            height = max(1, round(transformed.height * scale_percent / 100))
            transformed = transformed.resize((width, height), Image.Resampling.LANCZOS)
            if alpha is not None:
                alpha = alpha.resize((width, height), Image.Resampling.LANCZOS)

        if alpha is not None and output.suffix.lower() not in {".jpg", ".jpeg"}:
            transformed.putalpha(alpha)

        transformed.save(output)
