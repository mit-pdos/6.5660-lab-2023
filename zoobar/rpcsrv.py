import os
import sys
import socket
import stat
import errno
import json
import rpclib
from debug import *

sys.path.append(os.getcwd())
import readconf

class RpcServer(object):
    def run_fifo(self, pn):
        while True:
            with open(pn, 'r') as f:
                req = f.read()
            try:
                (method, kwargs) = rpclib.parse_req(req)
                m = self.__getattribute__('rpc_' + method)
                ret = m(**kwargs)
                resp = rpclib.format_resp(ret)
                with open(pn, 'w') as f:
                    f.write(resp)
            except:
                ## Open and close the FIFO to wake up the client
                with open(pn, 'w') as f:
                    pass
                raise

    def run_sock(self, sock):
        lines = rpclib.buffered_readlines(sock)
        for req in lines:
            (method, kwargs) = rpclib.parse_req(req)
            m = self.__getattribute__('rpc_' + method)
            ret = m(**kwargs)
            sock.sendall(rpclib.format_resp(ret).encode('ascii') + b'\n')

    def run_fork(self, port):
        print("Running on port %s" % port)
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('', int(port)))

        # Make sure there are no buffered writes before forking
        sys.stdout.flush()
        sys.stderr.flush()

        server.listen(5)
        while True:
            conn, addr = server.accept()
            pid = os.fork()
            if pid == 0:
                # fork again to avoid zombies
                if os.fork() <= 0:
                    self.set_caller_ip(addr[0])
                    self.run_sock(conn)
                    sys.exit(0)
                else:
                    sys.exit(0)
            conn.close()
            os.waitpid(pid, 0)

    def set_caller_ip(self, ip):
        self.caller = None
        conf = readconf.read_conf()
        for svcname in conf.svcs():
            if ip == conf.lookup_host(svcname)[0]:
                self.caller = svcname
