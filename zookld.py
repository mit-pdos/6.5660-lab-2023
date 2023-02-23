#!/usr/bin/env python3

import os
import sys
import zookconf

def main():
    if len(sys.argv) == 2:
        zookconf.boot(sys.argv[1])
    else:
        zookconf.boot()

if __name__ == "__main__":
    zookconf.restart_with_cgroups()
    if os.geteuid() == 0:
        print("WARNING: Running zookld.py as root! In order to clean up "
        "containers from this run, you must run zookclean.py as root as well.",
        file=sys.stderr)
    main()
