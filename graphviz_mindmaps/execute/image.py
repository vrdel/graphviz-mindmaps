import os
import subprocess


def WriteDot(dotbuf, dotfile):
    outputfile = open(dotfile, "w")
    outputfile.write(dotbuf)
    outputfile.close()


def ScaleImg(argholder, gvroot):
    cmd = "gm convert -scale %s%% '%s' '%s'" % (
        argholder.scale,
        gvroot + argholder.jpgname,
        gvroot + argholder.jpgname,
    )
    subprocess.call(cmd, shell=True)


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
            os.remove("%s/doodle.png" % (path))
            os.removedirs(path)
    return []


def WriteImg(dotbuf, argholder, gvroot, title, notitle, tmpdir):
    gvroot, argholder.jpgname = ResolveOutputRoot(gvroot, argholder.jpgname)

    proc = subprocess.Popen(["dot", "-Tjpg", "-o", gvroot + argholder.jpgname], stdin=subprocess.PIPE)
    proc.communicate(dotbuf.encode())

    subprocess.call(
        "gm convert -shave 2x2 '%s' '%s'" % (gvroot + argholder.jpgname, gvroot + argholder.jpgname),
        shell=True,
    )

    if not notitle:
        subprocess.call("montit -s s -t '%s' '%s'" % (title, gvroot + argholder.jpgname), shell=True)

    if argholder.scale:
        ScaleImg(argholder, gvroot)

    if argholder.preview:
        subprocess.call(
            "FvwmCommand 'All (galapix:*%s*) Close'"
            % argholder.jpgname.split("/")[1]
            if "/" in argholder.jpgname
            else argholder.jpgname,
            shell=True,
        )
        subprocess.Popen(["galaview.sh", gvroot + argholder.jpgname])

    tmpdir = CleanupTmpdir(tmpdir)

    next_dotbuf = ""
    next_notitle = False
    if not argholder.mtg:
        argholder.jpgname = None

    return {
        "gvroot": gvroot,
        "dotbuf": next_dotbuf,
        "tmpdir": tmpdir,
        "notitle": next_notitle,
    }
