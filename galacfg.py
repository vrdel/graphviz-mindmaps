#!/home/daniel/.pyenv/versions/vrdel-apps-py27/bin/python

import os, sys, sqlite3, math, time, signal
import socket, select, subprocess, ConfigParser, errno
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

CFG = os.environ['HOME'] + "/.galapix/galapix.cfg"

def cleanup(server, sock):
    server.close()
    os.unlink(sock)
    sys.exit(1)

def start(dirp, dbp, geom, title):
    rows = []

    if os.path.exists(dbp + "/cache3.sqlite3"):

        conn = sqlite3.connect(dbp + "/cache3.sqlite3")
        # conn.text_factory = str
        cur = conn.cursor()

        for f in os.listdir(dirp):
            f = dirp + "/" + f
            f = "%%%s%%" % f
            tup = (f.decode('utf-8'), )

            cur.execute('SELECT fileid, url, mtime FROM files WHERE url LIKE ?', tup)
            rows = cur.fetchall()


            for i in rows:
                dbid = i[0]
                dbpath = i[1].replace("file:", "")
                dbmtime = i[2]

                try:
                    filestat = os.stat(dbpath)
                    filemtime = math.trunc(filestat.st_mtime)
                except os.error:
                    cur.execute('DELETE FROM files WHERE fileid == ?', (dbid, ))
                    cur.execute('DELETE FROM tiles WHERE fileid == ?', (dbid, ))
                else:
                    if filemtime > dbmtime:
                        im = Image.open(dbpath)
                        t = (filemtime, filestat.st_size, im.size[0], im.size[1], dbid)
                        cur.execute('UPDATE files SET mtime=?, size=?, width=?, height=? WHERE fileid == ?', t)
                        cur.execute('DELETE FROM tiles WHERE fileid == ?', (dbid, ))

            conn.commit()

        conn.close()

    exestring = "galapix.sdl --threads 6 -g %s -d %s --title %s view" % (geom, dbp, title)
    exestring += ' ' + dirp

    return subprocess.Popen(exestring, shell=True)

def main():
    Settings = {}
    GalaInstan = {}

    class proc(subprocess.Popen):
        pass

    config = ConfigParser.ConfigParser()
    config.read(CFG)

    pixsock = config.defaults().get("pixsock")

    try:
        os.unlink(pixsock)
    except OSError:
        if os.path.exists(pixsock):
            raise

    try:
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(pixsock)
        server.listen(1)
    except socket.error as m:
        print m
        sys.exit(1)

    poller = select.poll()
    poller.register(server.fileno(), select.POLLIN)

    def sigcleanup(*sock):
        server.close()
        os.unlink(sock)
        sys.exit(1)

    class StaticVar:
        NumInstan = 0

    def chldcleanup(*msg):
        pid, status = os.wait()
        match = ""

        for inst in GalaInstan:
            if pid == GalaInstan[inst]["pid"]:
                match = inst
        if match:
            del GalaInstan[match]

        StaticVar.NumInstan -= 1
        if StaticVar.NumInstan == 0:
            cleanup(server, pixsock)
            sys.exit(1)


    for section in config.sections():
        if section.startswith("Dir"):
            Settings["dirp"] = config.get(section, "dirpath")
            Settings["dbp"] = config.get(section, "dbpath")
            Settings["title"] = config.get(section, "wintitle")
            Settings["geom"] = config.get(section, "geometry")
            proc = start(Settings["dirp"], Settings["dbp"], Settings["geom"], Settings["title"])
            Settings["pid"] = proc.pid
            GalaInstan[Settings["title"]] = Settings
            Settings = {}
            StaticVar.NumInstan = len(GalaInstan)

    signal.signal(signal.SIGCHLD, chldcleanup)
    signal.signal(signal.SIGTERM, sigcleanup)

    while True:
        try:
            event = poller.poll(None)
            if event[0][1] & select.POLLIN:
                conn, addr = server.accept()
                data = conn.recv(64)
                data = data.split()
                if data[1] == "restart":
                    signal.signal(signal.SIGCHLD, signal.SIG_IGN)
                    for inst in GalaInstan:
                        if data[0] in inst:
                            ret = os.kill(GalaInstan[inst]["pid"], signal.SIGTERM)
                            print(ret)
                            time.sleep(1)
                            proc = start(GalaInstan[inst]["dirp"], GalaInstan[inst]["dbp"], GalaInstan[inst]["geom"], GalaInstan[inst]["title"])
                            GalaInstan[inst]["pid"] = proc.pid
                            print(GalaInstan[inst]["pid"])
                        elif data[0] == "all":
                            os.kill(GalaInstan[inst]["pid"], signal.SIGTERM)
                            time.sleep(1)
                            proc = start(GalaInstan[inst]["dirp"], GalaInstan[inst]["dbp"], GalaInstan[inst]["geom"], GalaInstan[inst]["title"])
                            GalaInstan[inst]["pid"] = proc.pid

                    signal.signal(signal.SIGCHLD, chldcleanup)


        except KeyboardInterrupt:
            cleanup(server, pixsock)

        except select.error as m:
            if m[0] == errno.EINTR:
                poller.unregister(server.fileno())
                poller = select.poll()
                poller.register(server.fileno(), select.POLLIN)

main()
