from dataclasses import dataclass, field


@dataclass
class NodePrepState:
    ntype: str = ""
    wordcolor: list = field(default_factory=list)
    wordfsize: list = field(default_factory=list)
    wordfstyle: list = field(default_factory=list)
    linecolor: list = field(default_factory=list)
    linefsize: list = field(default_factory=list)
    linefstyle: list = field(default_factory=list)
    linefont: list = field(default_factory=list)
    linedate: list = field(default_factory=list)
    sgcolor: list = field(default_factory=list)
    sgtitle: list = field(default_factory=list)
    sgstyle: list = field(default_factory=list)
    edgecolor: list = field(default_factory=list)
    edgestyle: list = field(default_factory=list)
    edgend: list = field(default_factory=list)
    edgethick: list = field(default_factory=list)
    edglabel: list = field(default_factory=list)
    symbcolor: list = field(default_factory=list)
    symbsize: list = field(default_factory=list)
    symblist: list = field(default_factory=list)
    fontname: str | None = None
    bgcolor: str | None = None
    fgcolor: str | None = None
    child_subgraphs: bool | None = None

    def edgeattrs(self):
        edgeattrs = ""
        for values in [self.edgecolor, self.edgestyle, self.edgethick, self.edgend, self.edglabel]:
            if values:
                edgeattrs += " " + values[0]
        return edgeattrs

    def sgcolor_value(self):
        return self.sgcolor[0] if self.sgcolor else None

    def sgtitle_value(self):
        return self.sgtitle[0] if self.sgtitle else None

    def sgstyle_value(self):
        return self.sgstyle[0] if self.sgstyle else None


def Skip(maplist, s=None, lsinw=None):
    if maplist:
        seen_lmeta = set()
        j = 0
        while j < len(maplist):
            if lsinw and len(maplist[j]) > 2 and type(maplist[j][2]) == dict:
                lmeta = maplist[j][2]
                lmeta_id = id(lmeta)
                if lmeta_id not in seen_lmeta and lmeta.get("lineskip") is not None:
                    lmeta["lineskip"] += lsinw
                    seen_lmeta.add(lmeta_id)
            if s:
                maplist[j][0] += s
            j += 1


def SkipPositive(maplist, s):
    if not maplist or not s:
        return
    j = 0
    while j < len(maplist):
        if maplist[j][0] > 0:
            maplist[j][0] += s
        j += 1


def SkipUnscopedWords(maplist, s):
    if not maplist or not s:
        return

    j = 0
    while j < len(maplist):
        lmeta = maplist[j][2] if len(maplist[j]) > 2 else None
        if not (type(lmeta) == dict and lmeta.get("lineskip") is not None):
            maplist[j][0] += s
        j += 1


def SkipPositiveLineScopedWords(maplist, lsinw):
    if not maplist or not lsinw:
        return

    seen_lmeta = set()
    j = 0
    while j < len(maplist):
        lmeta = maplist[j][2] if len(maplist[j]) > 2 else None
        if type(lmeta) == dict and lmeta.get("lineskip") is not None:
            lmeta_id = id(lmeta)
            if lmeta_id not in seen_lmeta and lmeta["lineskip"] > 0:
                lmeta["lineskip"] += lsinw
                seen_lmeta.add(lmeta_id)
        j += 1
