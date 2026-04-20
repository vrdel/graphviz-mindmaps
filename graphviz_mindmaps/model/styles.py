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
