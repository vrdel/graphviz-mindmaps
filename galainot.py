#!/home/daniel/.pyenv/versions/vrdel-apps-py27/bin/python

import pyinotify, os, sys, signal, socket, select, errno, multiprocessing
import subprocess, time, re, threading, thread, ConfigParser, fcntl

CFG = os.environ['HOME'] + "/.galapix/galapix.cfg"

def callcom(commexe, po, event=None):
	if not event:
		event = "gvmm.py"

	output = subprocess.check_output(commexe, shell=True)
	if po:
		output = output.replace("\n\n", "<EMPTYL>")
		output = output.split("<EMPTYL>")[0]
		print "- " + time.strftime("%H:%M:%S") + " [%s]" % (event) \
			+ ": " + output.replace("\n", " ")

def inotifymon(commexe):
	wdd = {}

	class EventHandler(pyinotify.ProcessEvent):
		def _restartinst(self, event, typ):
			if typ == "delete":
				if os.path.exists(event.pathname):
					del (wdd[event.pathname])
			elif typ == "create":
				wdd.update(wm.add_watch(event.pathname,mask))
			elif typ == "deleteself":
				del (wdd[event.pathname])
				if os.path.exists(event.pathname):
					wdd.update(wm.add_watch(event.pathname, mask))
			callcom(commexe, True, event.maskname)

		def process_IN_DELETE(self, event):
			self._restartinst(event, "delete")
		def process_IN_DELETE_SELF(self, event):
			self._restartinst(event, "deleteself")
		def process_IN_CREATE(self, event):
			self._restartinst(event, "create")
		def process_IN_MODIFY(self, event):
			self._restartinst(event, "modify")
		def process_IN_CLOSE_WRITE(self, event):
			self._restartinst(event, "in_close_write")

	wm = pyinotify.WatchManager()
	mask = pyinotify.IN_DELETE_SELF | pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_CLOSE_WRITE

	handler = EventHandler()

	wdd.update(wm.add_watch(sys.argv[1], mask, rec=True))
	for (dirpath, dirnames, filenames) in os.walk(sys.argv[1], followlinks=True):
		if filenames:
			for f in filenames:
				wdd.update(wm.add_watch(os.path.realpath(dirpath + '/' + f), mask))

	notifier = pyinotify.Notifier(wm, handler)
	notifier.loop()

def main():
	config = ConfigParser.ConfigParser()
	config.read(CFG)

	inotsock = config.defaults().get("inotsock")

	try:
		os.unlink(inotsock)
	except OSError:
		if os.path.exists(inotsock):
			raise

	try:
		server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		server.bind(inotsock)
		server.listen(1)
	except socket.error as m:
		print m
		sys.exit(1)


	commexe = ""
	commexe = " ".join(sys.argv[2:])

	callcom(commexe, False)

	proc = multiprocessing.Process(target=inotifymon, args=(commexe,))
	proc.start()

	poller = select.poll()
	poller.register(server.fileno(), select.POLLIN)

	while True:
		try:
			event = poller.poll(None)
			if event[0][1] & select.POLLIN:
				conn, addr = server.accept()
				data = conn.recv(64)
				callcom(commexe, True)

		except select.error as m:
			print m
			if m[0] == errno.EINTR:
				poller.unregister(server.fileno())
				poller = select.poll()
				poller.register(server.fileno(), select.POLLIN)

		except KeyboardInterrupt:
			print "KeyboardInterrupt"
			proc.terminate()
			proc.join()
			server.close()
			os.unlink(inotsock)
			sys.exit(1)

main()
