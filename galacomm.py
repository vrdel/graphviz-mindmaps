#!/home/daniel/.pyenv/versions/gvmm/bin/python

import os, sys, socket, select
import ConfigParser, argparse

CFG = os.environ['HOME'] + "/.galapix/galapix.cfg"

def main():

	config = ConfigParser.ConfigParser()
	config.read(CFG)

	class ArgHolder(object):
	    pass

	argholder = ArgHolder()

	parser = argparse.ArgumentParser()
	parser.add_argument('-r', dest = 'res', nargs = '?', default = 'NoSpec')
	parser.add_argument('-k', dest = 'kill', nargs = '?', default = 'NoSpec')

	parser.parse_args(namespace = argholder)

	pixsock = config.defaults().get("pixsock")

	try:
		sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		sock.connect(pixsock)
	except socket.error as m:
		print m
		sys.exit(1)

	if argholder.res:
		t = ("%s restart" % (argholder.res), )
		sock.send(t[0], 64)
	elif argholder.res == None:
		t = ("all restart", )
		sock.send(t[0], 64)
	elif argholder.kill:
		t = ("%s kill" % (argholder.kill), )
		sock.send(t[0], 64)
	elif argholder.kill == None:
		t = ("all kill", )
		sock.send(t[0], 64)


	sock.close()

main()
