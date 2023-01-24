#!/usr/bin/env python3

from wsgiref.handlers import CGIHandler

from __init__ import *

if __name__ == "__main__":
    CGIHandler().run(app)
