#!/usr/bin/python3

try:
    import inotify_simple
except:
    print('cannot import inotify_simple')
    import pip
    pip.main(['install', 'inotify_simple'])

import inotify_simple
import subprocess
import sys
import os
import signal

class Proxy(object):
    def __init__(self, args):
        self.proc = None
        self.args = args
        signal.signal(signal.SIGTERM, self.stop_signal)
        signal.signal(signal.SIGINT, self.stop_signal)
        self.restart()

    def stop_signal(self, signum, frame):
        self.stop()
        sys.exit()

    def stop(self):
        if self.proc is not None:
            self.proc.kill()
            self.proc = None

    def restart(self):
        self.stop()
        self.proc = subprocess.Popen(self.args, stdout=sys.stdout, stderr=sys.stderr)

inotify = inotify_simple.INotify()
flags = inotify_simple.flags.CREATE | inotify_simple.flags.MODIFY | inotify_simple.flags.DELETE
inotify.add_watch(".", flags)
tls_key = "tls.key"
tls_cert = "tls.cert"
p = Proxy([
    "/usr/local/bin/ghostunnel",
    "server",
    "--listen", ":8443",
    "--target", "localhost:8080",
    "--key", tls_key,
    "--cert", tls_cert,
    "--disable-authentication",
])
relevant_files = [tls_key, tls_cert]

while True:
    events = inotify.read()
    relevant = any([ev.name in relevant_files for ev in events])
    if relevant:
        p.restart()
