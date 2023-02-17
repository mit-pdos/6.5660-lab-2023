#!/usr/bin/env python3

import os
import sys
import atexit
import time
import subprocess
import traceback
import sqlite3
from typing import List

from stat import *

thisdir = os.path.dirname(os.path.abspath(__file__))
verbose = False

def green(s: str) -> str:
    return '\033[1;32m%s\033[m' % s

def red(s: str) -> str:
    return '\033[1;31m%s\033[m' % s

def log(*m: str) -> None:
    print(" ".join(m), file=sys.stderr)

def log_exit(*m: str) -> None:
    log(red("ERROR:"), *m)
    exit(1)

def file_read(pn: str) -> str:
    with open(pn) as fp:
        return fp.read()

def sh(cmd: str, exit_onerr: bool = True) -> None:
    if verbose: log("+", cmd)
    if os.system(cmd) != 0 and exit_onerr:
        log_exit("running shell command:", cmd)

def killall() -> None:
    sh("killall zookld zookd zookfs zookd-exstack zookfs-exstack zookd-nxstack zookfs-nxstack >/dev/null 2>&1", exit_onerr=False)

    scripts = "echo-server.py auth-server.py bank-server.py".split(" ")
    for script in scripts:
        sh("pkill -f 'python3 .*%s' >/dev/null 2>&1" % script, exit_onerr=False)

def setup() -> None:
    log("+ removing zoobar db")
    sh("rm -rf zoobar/db")

    log("+ running make.. output in /tmp/make.out")
    sh("make clean >/dev/null")
    sh("make all >/tmp/make.out 2>&1")
    sh("touch /tmp/zook-start-wait")

    log("+ running zookd in the background.. output in /tmp/zookd.out")
    zookd_out = open("/tmp/zookd.out", "w")
    subprocess.Popen(["./zookd", "8080"], stdout=zookd_out, stderr=zookd_out)
    
    atexit.register(killall)
    sh("inotifywait -qqe delete_self -t 20 /tmp/zook-start-wait 2>/dev/null", False)

import z_client
def check_ex0() -> None:
    x = z_client.check('127.0.0.1')
    if not x[0]:
        log(red("FAIL"), "Zoobar app functionality", x[1])
        exit(1)
    else:
        log(green("PASS"), "Zoobar app functionality")

def main() -> None:
    if '-v' in sys.argv:
        global verbose
        verbose = True
        
    try:
        setup()
        check_ex0()
    except Exception:
        log_exit(traceback.format_exc())

if __name__ == "__main__":
    main()
