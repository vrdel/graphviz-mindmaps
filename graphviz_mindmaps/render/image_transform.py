from pathlib import Path

from PIL import Image, ImageOps


def TransformImage(source: str | Path, output: str | Path, negate: bool = False, grayscale: bool = False) -> None:
    source = Path(source)
    output = Path(output)

    with Image.open(source) as image:
        has_alpha = "A" in image.getbands() or "transparency" in image.info
        rgba = image.convert("RGBA") if has_alpha else None
        alpha = rgba.getchannel("A") if rgba else None
        transformed = rgba.convert("RGB") if rgba else image.convert("RGB")

        if negate:
            transformed = ImageOps.invert(transformed)
        if grayscale:
            transformed = ImageOps.grayscale(transformed)

        if alpha is not None and output.suffix.lower() not in {".jpg", ".jpeg"}:
            transformed.putalpha(alpha)

        transformed.save(output)
