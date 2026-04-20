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
    tempfile_module: object
    subprocess_module: object
    parse_fname_line: object
    write_dot: object
    write_img: object
    write_montage: object
    send_restart_msg: object
