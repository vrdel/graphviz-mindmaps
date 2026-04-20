import fnmatch
import os
import subprocess


def CheckCM(img):
    cmfile = None

    for fil in os.listdir("."):
        if fnmatch.fnmatch(fil, "*.cm"):
            fo = open(fil)
            lines = fo.readlines()
            for line in lines:
                if img in line:
                    cmfile = fil
            fo.close()
    return cmfile


def WriteMontage(argholder, gvroot, send_restart_msg):
    imgarg = argholder.jpgname.split("/")
    if argholder.jpgname.startswith("gv/"):
        os.chdir(gvroot + "/".join(imgarg[0:2]))
        cmfile = CheckCM(imgarg[2])
    else:
        print("montage building should be in %s/gv/" % (gvroot[0:-1]))
        raise SystemExit(1)

    if cmfile:
        subprocess.call(["montage.py", cmfile])
        send_restart_msg("rsync call", "inotsock")
    else:
        print("%s not found in any %s/*.cm" % (imgarg[2], gvroot + "/".join(imgarg[0:2])))
        raise SystemExit(1)
