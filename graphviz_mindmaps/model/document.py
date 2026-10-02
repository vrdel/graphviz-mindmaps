from dataclasses import dataclass, field


class SourceLine(str):
    """A raw outline line with provenance, compatible with legacy string parsers."""

    def __new__(cls, text, filename="<stdin>", number=1, document=0):
        instance = super().__new__(cls, text)
        instance.filename = filename
        instance.number = number
        instance.document = document
        return instance


@dataclass
class MarkdownBody:
    source: str
    filename: str
    title: str
    attribute_line: int
    # (original line number, payload column), including prefixed blank lines.
    locations: list = field(default_factory=list)

    def error(self, message, source_line=None):
        line = self.attribute_line
        if source_line is not None and 0 <= source_line < len(self.locations):
            line = self.locations[source_line][0]
        return ValueError(f"{self.filename}:{line}: Markdown node {self.title!r}: {message}")


@dataclass
class RenderSession:
    dotbuf: str = ""
    title: str = ""
    notitle: bool = False
    bgcolor: str = ""
    tmpdir: list = field(default_factory=list)
    gvroot: str = ""


@dataclass
class RenderRuntime:
    fontawesome_symb: dict
    default_bgcolor: str
    theme_name: str = "default"
