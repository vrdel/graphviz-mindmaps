from dataclasses import dataclass, field


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
