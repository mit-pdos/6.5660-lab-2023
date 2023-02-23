#!/usr/bin/env python3

import sys

import zookconf

def main():
    if len(sys.argv) == 2:
        zookconf.shutdown(sys.argv[1])
    else:
        zookconf.shutdown()

if __name__ == "__main__":
    zookconf.restart_with_cgroups()
    main()
