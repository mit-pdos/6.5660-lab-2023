import os
import sys
import socket
import stat
import errno
import json

def parse_req(req):
    return json.loads(req)

def format_req(method, kwargs):
    return json.dumps([method, kwargs])

def parse_resp(resp):
    return json.loads(resp)

def format_resp(resp):
    return json.dumps(resp)

def buffered_readlines(sock):
    buf = ''
    while True:
        while '\n' in buf:
            (line, nl, buf) = buf.partition('\n')
            yield line
        try:
            newdata = sock.recv(4096).decode('ascii')
            if newdata == '':
                break
            buf += newdata
        except IOError as e:
            if e.errno == errno.ECONNRESET:
                break

class RpcClient(object):
    def __init__(self, sock):
        self.sock = sock
        self.lines = buffered_readlines(sock)

    def call(self, method, **kwargs):
        self.sock.sendall(format_req(method, kwargs).encode('ascii') + b'\n')
        return parse_resp(next(self.lines))

    def close(self):
        self.sock.close()

    ## __enter__ and __exit__ make it possible to use RpcClient()
    ## in a "with" statement, so that it's automatically closed.
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

## This FIFO-based RPC client exists to deal with the fact that WASI does
## not yet have complete support for sockets; e.g., see these issues:
##
##    https://github.com/bytecodealliance/wasmtime/issues/3936
##    https://github.com/python/cpython/issues/96320
##
## To work around this, we issue RPCs through a FIFO special file.
class RpcClientFifo(object):
    def __init__(self, pn):
        self.pn = pn

    def call(self, method, **kwargs):
        req = format_req(method, kwargs)
        with open(self.pn, 'w') as f:
            f.write(req)
        with open(self.pn, 'r') as f:
            resp = f.read()
        return parse_resp(resp)

    def close(self):
        pass

    ## __enter__ and __exit__ make it possible to use RpcClientFifo()
    ## in a "with" statement, so that it's automatically closed.
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

def client_connect(host):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("Connecting to %s:%d" % (host[0], host[1]))
    sock.connect(host)
    return RpcClient(sock)
