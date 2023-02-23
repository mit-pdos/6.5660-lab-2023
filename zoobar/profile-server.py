#!/usr/bin/env python3

import base64
import rpclib
import rpcsrv
import sys
import os
import hashlib
import bank
import zoodb
import tempfile
import shutil
import signal
import wasmtime
import threading
import time

from debug import *

## NOTE: you will likely need to change how the code in ProfileAPIServer
## accesses the bank state, based on your design for privilege-separating
## the bank.
class ProfileAPIServer(rpcsrv.RpcServer):
    def __init__(self, user, visitor, pcode):
        self.user = user
        self.visitor = visitor
        self.pcode = pcode

    def rpc_get_self(self):
        return self.user

    def rpc_get_visitor(self):
        return self.visitor

    def rpc_get_xfers(self, username):
        return bank.get_log(username)

    def rpc_get_user_info(self, username):
        return { 'username': self.user,
                 'profile': self.pcode,
                 'zoobars': bank.balance(username),
               }

    def rpc_xfer(self, target, zoobars):
        bank.transfer(self.user, target, zoobars)

class FifoServer(object):
    def __init__(self, server, fifo_pn):
        os.mkfifo(fifo_pn)
        self.server = server
        self.fifo_pn = fifo_pn
        self.pid = None

    def __enter__(self):
        self.pid = os.fork()
        if self.pid == 0:
            server.run_fifo(self.fifo_pn)
            os._exit(0)

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.kill(self.pid, signal.SIGTERM)

class ProfileServer(rpcsrv.RpcServer):
    def rpc_run(self, pcode, user, visitor):
        ## This function needs to run the Python profile code in pcode
        ## and return the output from that execution.

        ## The Python interpreter expects to be able to access files
        ## from wasm_python_dir as "/" when it runs.
        wasm_python_dir = '/usr/local/share/Python-3.11.0-wasm32-wasi-16'

        ## We create a per-user state directory for files written by
        ## that user's profile.  To ensure we correctly handle usernames
        ## with arbitrary characters (such as slash, dot, etc), we just
        ## compute a hash of the username and use that in the pathname.
        user_hash = hashlib.sha256(user.encode('utf-8')).hexdigest()
        userdir = os.path.join('/tmp/', user_hash)
        if not os.path.exists(userdir):
            os.mkdir(userdir)

        ## Finally, we create a temporary directory td just for this
        ## execution of the user's profile code.  We use this temporary
        ## directory to create a way for the code running inside the
        ## WebAssembly sandbox to communicate with the ProfileAPIServer,
        ## through a special FIFO file at td/fifo.
        with tempfile.TemporaryDirectory() as td, FifoServer(ProfileAPIServer(user, visitor, pcode), td + "/fifo") as ps:

            ## Your job is to set up the environment to run pcode correctly
            ## (for exercise 10) and safely (for exercise 11).

            ## You will need to figure out where and how to supply the code
            ## that needs to run.  You can tell python.wasm to run specific
            ## python code by passing that filename as an argument at the
            ## end of wasi.argv.  Note that the executable profiles expect
            ## to be able to import the library code from api.py in order
            ## to interact with the ProfileAPIServer through the FIFO.

            ## The RPC client in the WebAssembly sandbox (from api.py) expects
            ## to communicate with the ProfileAPIServer through a FIFO located
            ## at /run/fifo.  You will need to arrange for this to work.

            ## You will also need to figure out how to get the output from
            ## the WebAssembly sandbox and return it from this function.
            ## You can get wasmtime to write the output to a file by setting
            ## wasi.stdout_file to the pathname where the output should go.

            ## The profile code expects to be able to read and write persistent
            ## state in the /data directory.  You will need to arrange for this
            ## to work.

            ## For exercise 11, you will need to ensure that the executable
            ## profile code cannot tamper with the Python library code.  One plan
            ## could be to create a separate copy so that it doesn't matter if
            ## it's corrupted.  Another plan could be to set the Unix user ID of
            ## this process to something other than root (e.g., 5660) using
            ## os.setuid; since the library files in wasm_python_dir are owned by
            ## root, the wasmtime runtime won't be able to modify them then.

            ## Finally, for exercise 11, you will need to deal with profile code
            ## that doesn't terminate.  The wasmtime runtime allows interrupting
            ## a running module by calling engine.increment_epoch().

            config = wasmtime.Config()
            config.wasm_simd = False
            config.epoch_interruption = True

            engine = wasmtime.Engine(config)
            mod = wasmtime.Module.from_file(engine, '%s/python.wasm' % wasm_python_dir)
            linker = wasmtime.Linker(engine)
            linker.define_wasi()

            wasi = wasmtime.WasiConfig()
            wasi.inherit_stderr()
            wasi.argv = ['python.wasm', ]
            wasi.preopen_dir(wasm_python_dir, '/')

            store = wasmtime.Store(engine)
            store.set_wasi(wasi)

            ## Calling set_epoch_deadline(1) means that the running module will
            ## be interrupted the first time someone calls engine.increment_epoch().
            store.set_epoch_deadline(1)

            inst = linker.instantiate(store, mod)
            start = inst.exports(store)['_start']
            try:
                start(store)
            except wasmtime.ExitTrap as e:
                if e.code != 0:
                    raise e

            return ''

if len(sys.argv) != 2:
    print(sys.argv[0], "too few args")

s = ProfileServer()
s.run_fork(sys.argv[1])
