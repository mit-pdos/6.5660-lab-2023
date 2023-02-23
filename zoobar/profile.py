from flask import g
from debug import *

import os
import rpclib
import traceback

sys.path.append(os.getcwd())
import readconf

def run_profile(user):
    try:
        pcode = user.profile
        pcode = pcode.replace('\r\n', '\n')
        host = readconf.read_conf().lookup_host('profile')
        with rpclib.client_connect(host) as c:
            return c.call('run', pcode=pcode,
                                 user= user.username,
                                 visitor=g.user.person.username)
    except Exception as e:
        traceback.print_exc()
        return 'Exception: ' + str(e)
