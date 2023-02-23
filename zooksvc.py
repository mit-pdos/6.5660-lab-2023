#!/usr/bin/env python3

import fcntl
import os
import re
import sys
import socket
import struct
import subprocess

import readconf

#
# Start cmd inside container
#

def start(k):
    ct = readconf.read_conf(d="/app")
    if k == "main":
        (rfd, wfd) = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM, 0)
        sock = start_server(k, ct.lookup("main", "port"))
        conf = ct.conf(k)
        svcs = conf.http_svcs()
        sendnsvc(len(svcs), wfd)
        sendct(wfd, svcs, ct, 'url', 'string')
        sendct(wfd, svcs, ct, 'lxcbr', 'int')
        sendct(wfd, svcs, ct, 'port', 'int')
        p = clone(conf, rfd, sock)
    else:
        p = clone(ct.conf(k))
    return p

def start_server(host, port):
    print("zooksvc.py: dispatcher %s, port %s" % (host, port))
    sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sockfd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # fcntl.fcntl(sockfd.fileno(), fcntl.F_SETFD, fcntl.FD_CLOEXEC)
    sockfd.bind(('', int(port)))
    sockfd.listen(5)
    return sockfd

def clone(conf, fd=None, sock=None):
    cmd = conf.lookup('cmd')
    args = ["./" + cmd]
    if fd != None and sock != None:
        os.set_inheritable(fd.fileno(), True)
        os.set_inheritable(sock.fileno(), True)
        args.append(str(fd.fileno()))
        args.append(str(sock.fileno()))
    else:
        args.append(conf.lookup('port'))
    d = conf.lookup('dir')
    print("zooksvc.py: running %s" % args)
    p = subprocess.Popen(args, cwd=d, close_fds=False)
    return p

def sendct(wfd, svcs, ct, n, form):
    for k in svcs:
        send(ct.conf(k), wfd, n, form)

def sendnsvc(nsvc, wfd):
    b = struct.pack('<i', nsvc)
    wfd.sendall(b)

def send(conf, wfd, n, form):
    if form == 'string':
        b = bytes(conf.lookup(n), 'utf-8')
        s = struct.pack('<%ds' % len(b), b)
        b = struct.pack('<i', len(s))
        wfd.sendall(b)
        wfd.sendall(s)
    elif form == 'int':
        b = struct.pack('<i', int(conf.lookup(n)))
        wfd.sendall(b)
    else:
        print("unknown format", form)

def main():
    if len(sys.argv) != 2:
        print(sys.argv[0], "too few args")
        sys.exit(1)
    start(sys.argv[1])

if __name__ == "__main__":
    main()
