import os
import re

CONF = "zook.conf"

class Conf(object):
    def __init__(self, name):
        self.conf = {}

    def add(self, n, v):
        if n in self.conf:
            if isinstance(self.conf[n] , (list,)):
                self.conf[n].append(v)
            else:
                t = self.conf[n]
                self.conf[n] = [t]
                self.conf[n].append(v)
        else:
            self.conf[n] = v

    def lookup(self, k):
        return self.conf.get(k)

    def http_svcs(self):
        svcs = self.conf['http_svcs']
        svcs = svcs.split(",")
        r = []
        for s in svcs:
            r.append(s.strip())
        return r

    def __str__(self):
        return str(self.conf)

class ConfTable(object):
    def __init__(self):
        self.table = {}

    def isservice(self, k):
        return self.table.get(k) != None

    def add(self, n, v):
        self.table[n] = v

    def conf(self, svc):
        return self.table[svc]

    def lookup(self, svc, key):
        c = self.table[svc]
        return c.lookup(key)

    def lookup_host(self, svc):
        c = self.table[svc]
        return ('10.1.%s.4' % c.lookup('lxcbr'), int(c.lookup('port')))

    def __str__(self):
        s = ""
        for k in self.table:
            s += k + ":" + str(self.table[k]) + "\n"
        return s

    def nsvc(self):
        return len(self.table) - 1 # don't include main

    def svcs(self):
        return self.table.keys()


def read_conf(d="."):
    ct = ConfTable()
    c = None
    l = 0
    with open(os.path.join(d, CONF)) as f:
        for line in f:
            l += 1
            if re.match(r'#.*', line) != None:
                continue
            m = re.match(r'\[(\w*)\]', line)
            if m != None:
                n = m.group(1)
                c = Conf(n)
                ct.add(n, c)
            else:
                m = re.match(r'\s*(\w*)\s*=\s*(.*)', line)
                if m != None:
                    if c == None:
                        print("conf file:", l, "def without section")
                    else:
                        c.add(m.group(1), m.group(2))
    return ct
