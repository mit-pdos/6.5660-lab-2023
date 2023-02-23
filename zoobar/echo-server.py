#!/usr/bin/env python3

import rpcsrv
import sys
from debug import *

class EchoRpcServer(rpcsrv.RpcServer):
    def rpc_echo(self, s):
        return 'You said "%s" from %s' % (s, self.caller)

if len(sys.argv) != 2:
    print(sys.argv[0], "too few args")

s = EchoRpcServer()
s.run_fork(sys.argv[1])
