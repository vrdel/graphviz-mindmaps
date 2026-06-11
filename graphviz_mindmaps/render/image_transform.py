from pathlib import Path

from PIL import Image, ImageFilter, ImageOps


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

        if scale_percent is not None:
            width = max(1, round(transformed.width * scale_percent / 100))
            height = max(1, round(transformed.height * scale_percent / 100))
            transformed = transformed.resize((width, height), Image.Resampling.LANCZOS)
            if alpha is not None:
                alpha = alpha.resize((width, height), Image.Resampling.LANCZOS)

        if alpha is not None and output.suffix.lower() not in {".jpg", ".jpeg"}:
            transformed.putalpha(alpha)

        transformed.save(output)
