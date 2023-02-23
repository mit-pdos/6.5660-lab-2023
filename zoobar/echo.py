from flask import g, render_template, request
from debug import *
import os
import rpclib
import sys

sys.path.append(os.getcwd())
import readconf

@catch_err
def echo():
    host = readconf.read_conf().lookup_host('echo')
    with rpclib.client_connect(host) as c:
        ret = c.call('echo', s=request.args.get('s', ''))
        return render_template('echo.html', s=ret)
