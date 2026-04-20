import configparser
import socket


def SendRestartMSG(cfg, sockwildcard, sockcfg=None):
    config = configparser.ConfigParser()
    config.read(cfg)

    sockp = config.defaults().get(sockcfg)

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(sockp)
    except socket.error as exc:
        print(sockcfg)
        print(exc)
    else:
        sock.send(("%s restart" % (sockwildcard[0])).encode(), 64)
        sock.close()
