#!/usr/bin/env python3

import datetime
import os
import sys
import atexit
import time
import subprocess
import traceback
import re
import urllib.parse
import base64
import sqlite3
import lxc
import zookconf
import threading

import z_client

from stat import *

thisdir = os.path.dirname(os.path.abspath(__file__))
verbose = False
serverip = "10.1.0.4"

def green(s):
    return '\033[1;32m%s\033[m' % s

def red(s):
    return '\033[1;31m%s\033[m' % s

def log(*m):
    print(" ".join(m), file=sys.stderr)

def ok(*m):
    log(green("PASS:"), *m)

def fail(*m):
    log(red("FAIL:"), *m)

def log_exit(*m):
    log(red("ERROR:"), *m)
    killall()
    exit(1)

def fail_exit(*m):
    log(red("FAIL:"), *m)
    killall()
    exit(1)

def file_read_raw(pn):
    with open(pn, "rb") as fp:
        return fp.read()

def file_read(pn):
    with open(pn) as fp:
        return fp.read()

def file_read_sz(pn, size=-1):
    with open(pn) as fp:
         return fp.read(size)

def log_to_file(*m):
    with open('/tmp/html.out', 'a') as fp:
        print(" ".join(m), file=fp)

def sh(cmd, exit_onerr=True):
    if verbose: log("+", cmd)
    if os.system(cmd) != 0 and exit_onerr:
        log_exit("running shell command:", cmd)

def clean_state(containers):
    for cn in containers:
        c = lxc.Container(cn)
        if c.running:
            c.attach_wait(lxc.attach_run_command, ["rm", "-rf", "/app/zoobar/db/"])

def check_run(containers):
    for cn in containers:
        c = lxc.Container(cn)
        if not c.running:
            fail_exit("Container %s should be running" % cn)

def check_dbexists(cn, name):
    c = lxc.Container(cn)
    if c.attach_wait(lxc.attach_run_command, ["test", "-e", "/app/zoobar/db/%s" % name]) != 0:
        fail("Container %s should have database %s" % (cn, name))
        return False
    return True

def check_nodb(cn):
    c = lxc.Container(cn)
    if c.attach_wait(lxc.attach_run_command, ["test", "-e", "/app/zoobar/db"]) == 0:
        fail("Container %s shouldn't have any databases" % cn)
        return False
    return True

def check_file(cn, pn):
    c = lxc.Container(cn)
    if c.attach_wait(lxc.attach_run_command, ["test", "-e", "%s" % pn]) != 0:
        return False
    return True

def ipaddr(c):
    ip = c.get_config_item('lxc.net.0.ipv4.address')
    return ip.split('/')[0]

def check_nocomm(src, dst):
    s = lxc.Container(src)
    d = lxc.Container(dst)
    try:
        ip = ipaddr(d)
    except KeyError:
        fail("Container %s not configured" % dst)
        return False
    with subprocess.Popen(["awk", ""], stdin=subprocess.PIPE) as filter:
        if s.attach_wait(lxc.attach_run_command, ["ping", "-nq", "-c", "5", "-i", "0.1", "-W", "1", ip], stdout=filter.stdin) == 0:
            fail("Container %s shouldn't be able to communite with %s" % (src, dst))
            return False
    return True

def check_comm(src, dst):
    s = lxc.Container(src)
    d = lxc.Container(dst)
    try:
        ip = ipaddr(d)
    except KeyError:
        fail("Container %s not configured" % dst)
        return False
    with subprocess.Popen(["awk", ""], stdin=subprocess.PIPE) as filter:
        if s.attach_wait(lxc.attach_run_command, ["ping", "-nq", "-c", "5", "-i", "0.1", "-W", "1", ip], stdout=filter.stdin) != 0:
            fail("Container %s should be able to communite with %s" % (src, dst))
            return False
    return True

def container_path(name, path):
    c = lxc.Container(name)
    return '/proc/%d/root/%s' % (c.init_pid, path)

def dbquery(container, dbfile, q):
    conn = sqlite3.connect(container_path(container, dbfile))
    cur  = conn.cursor()
    cur.execute(q)
    ret  = cur.fetchall()
    cur.close()
    conn.close()
    return ret

def db_tables(container, dbfile):
    rows = dbquery(container, dbfile, "SELECT name FROM sqlite_master WHERE type='table'")
    return [ r[0].lower() for r in rows ]

def column_in_table(container, dbfile, table, column):
    rows = dbquery(container, dbfile, "SELECT sql FROM sqlite_master WHERE type='table' AND name='%s'" % table)
    return column.lower() in rows[0][0].lower()

def check_db(ex, container, dbfile, table, columns):
    if not os.path.exists(container_path(container, dbfile)):
        fail(ex, "no db %s in %s" % (dbfile, container))
        return False
    if table.lower() not in db_tables(container, dbfile):
        fail(ex, "%s table not present in %s" % (table, dbfile))
    elif not all([ column_in_table(container, dbfile, table, c) for c in columns ]):
        fail(ex, "missing some column in %s table of %s" % (table, dbfile))
    else:
        return True
    return False

def setup_env():
    sh("./zookstop.py", exit_onerr=False)
    sh("./zookld.py", exit_onerr=False)
    clean_state(["zookfs", "dynamic", "auth", "bank"])

def killall():
    sh("./zookstop.py", exit_onerr=False)

def setup():
    log("+ setting up containers..")
    setup_env()

def check_ex1():
    x = z_client.check(serverip)
    if not x[0]:
        fail_exit("App functionality", x[1])
    else:
        ok("App functionality")

def check_ex2():
    check_run(["dynamic", "static"])
    c = lxc.Container('zookfs')
    if c.running:
        fail_exit("Container zookfs shouldn't be running")
    if check_nodb("static") and check_dbexists("dynamic", "person"):
        ok("Exercise 2: separation")

def check_ex3():
    if check_nocomm("static", "dynamic") and check_comm("main", "static"):
        ok("Exercise 3: fwrule")

def check_ex4_1():
    authdb = "/app/zoobar/db/cred/cred.db"
    check_0 = check_db("Exercise 4:", "auth", authdb,
                       "cred", ['password', 'token'])
    return check_0

def check_ex4_2():
    persondb = "/app/zoobar/db/person/person.db"
    if any([ column_in_table('dynamic', persondb, "person", c) \
               for c in ['password', 'token'] ]):
        fail("Exercise 4:", "person table still has some cred table column")
        return False
    return True

def check_ex4():
    if check_dbexists("auth", "cred") and check_ex4_1() and check_ex4_2():
        ok("Exercise 4: separation")

def check_ex5():
    if check_nocomm("static", "dynamic") and check_nocomm("static", "auth") and check_nocomm("main", "auth") and check_comm("main", "static"):
        ok("Exercise 5: fwrule")

def check_ex6():
    dbfile = "/app/zoobar/db/cred/cred.db"
    if not os.path.exists(container_path('auth', dbfile)):
        fail("Exercise 6:", "no db %s in auth" % dbfile)
        return
    db = file_read_raw(container_path('auth', dbfile))
    if b"supersecretpassword" in db:
        fail("Exercise 6:", "plain-text password in database")
    else:
        ok("Exercise 6")

def check_ex7_1():
    persondb = "/app/zoobar/db/person/person.db"
    if column_in_table('dynamic', persondb, "person", "zoobars"):
        fail("Exercise 7:", "person table still has the zoobars column")
        return False
    return True

def check_ex7():
    bankdb = "/app/zoobar/db/bank/bank.db"
    check_0 = check_db("Exercise 7:", "bank", bankdb,
                       "bank", ['zoobars'])
    if check_0 and check_ex7_1():
        ok("Exercise 7")

def check_ex8():
    html_src, cookies_src = z_client.register("test8src", "aaa")
    html_dst, cookies_dst = z_client.register("test8dst", "bbb")

    # First, do a regular transfer with a server-side delay,
    # and make sure everything works.
    thtml = z_client.transfer(cookies_src, "test8dst", 3, 5)

    html_src, cookies_src = z_client.login("test8src", "aaa")
    x = z_client.check_zoobars(html_src, b"test8src", 7, "zoobar transfer did not deduct from sender")
    if not x[0]:
        fail("Exercise 8:", x[1])
        return False

    html_dst, cookies_dst = z_client.login("test8dst", "bbb")
    x = z_client.check_zoobars(html_dst, b"test8dst", 13, "zoobar transfer did not deposit to recipient")
    if not x[0]:
        fail("Exercise 8:", x[1])
        return False

    # Next, make sure that doing a transfer with an outdated cookie
    # fails (the token is changed by login).
    html_src2, cookies_src2 = z_client.login("test8src", "aaa")
    thtml = z_client.transfer(cookies_src, "test8dst", 3, 5)
    if thtml.find(b"Sent") >= 0:
        fail("Exercise 8:", "transfer request goes through with old cookies")
        return False

    # Next, do a transfer but also quickly log in while the transfer
    # is running, to force the token to change.
    html_src, cookies_src = z_client.login("test8src", "aaa")
    xfer_thread = threading.Thread(target=lambda: z_client.transfer(cookies_src, "test8dst", 3, 5))
    xfer_thread.start()

    # Wait a little bit for the transfer request to pass the initial
    # cookie check, and then force the token to change.
    time.sleep(1)
    html_src, cookies_src = z_client.login("test8src", "aaa")
    xfer_thread.join()

    # Make sure the transfer did not go through; should be still at 7 and 13.
    html_src, cookies_src = z_client.login("test8src", "aaa")
    x = z_client.check_zoobars(html_src, b"test8src", 7, "zoobar transfer went through with old token")
    if not x[0]:
        fail("Exercise 8:", x[1])
        return False

    html_dst, cookies_dst = z_client.login("test8dst", "bbb")
    x = z_client.check_zoobars(html_dst, b"test8dst", 13, "zoobar transfer went through with old token")
    if not x[0]:
        fail("Exercise 8:", x[1])
        return False

    ok("Exercise 8")

def check_ex9():
    if check_nocomm("static", "dynamic") and check_nocomm("static", "auth") and check_nocomm("main", "auth") and check_comm("main", "static") and check_nocomm("main", "bank"):
        ok("Exercise 9: fwrule")


#
# Part 4
#

def update_profile(cookie, code):
    payload = urllib.parse.quote_plus(code)
    result = z_client.post("http://%s:8080/zoobar/index.cgi/" % serverip, cookie,
           "profile_update=%s&profile_submit=Save" % payload)

def check_profile_internal(logmsg, code, prof_pat,
                           user1="test1", pass1="supersecretpassword",
                           user2="test2", pass2="pass"):
    ## login as user test1
    html1, cookies1 = z_client.login(user1, pass1)
    ## update test1 profile
    update_profile(cookies1, code)

    ## login as user test2
    html2, cookies2 = z_client.login(user2, pass2)

    ## fetch test1 profile
    vhtml = z_client.view_user(cookies2, user1)
    vhtml = vhtml.decode("utf-8")

    ## log profile output
    log_to_file("=" * 60)
    log_to_file(logmsg)
    log_to_file("")
    log_to_file(vhtml)
    log_to_file("")

    if prof_pat is None:
        return vhtml

    ## check for profile pattern
    ans = "Traceback" not in vhtml and re.search(prof_pat, vhtml, re.DOTALL) is not None
    #if not ans:
        #print "OOPS! $#$#$#$#$#"
        #print "pat",prof_pat
        #print vhtml
    return ans

## profile generation patterns
wrapper_pat = '''
try:
    if check():
        print("SUCCESS")
    else:
        print("ERROR : check failed")
except BaseException as e:
    import traceback
    print("ERROR : caught exception")
    print(traceback.format_exc())
'''

file_read_pat = '''#!python
def check():
    import os, base64
    print("Opening file %(path)s")
    fd = os.open("%(path)s", os.O_RDONLY)
    print("Opened file %(path)s")
    d  = os.read(fd, %(length)d)
    os.close(fd)
    d = d.decode('utf-8')
    print("Read '" + d + "' from file")
    return d == "%(data)s"
'''

file_write_pat = '''#!python
def check():
    import os
    print("Opening file %(path)s")
    fd = os.open("%(path)s", os.O_CREAT | os.O_RDWR)
    print("Opened file %(path)s")
    d  = "%(data)s"
    de  = "%(data)s".encode('utf-8')
    l  = os.write(fd, de)
    os.close(fd)
    print("Wrote " + d + " " + str(l) + " bytes")
    return l == len(d)
'''

def file_read_check(logmsg, sbpath, realpath=None, data=None,
                    user1="test1", pass1="supersecretpassword",
                    user2="test2", pass2="pass"):
    if not data:
        data = file_read_sz(realpath, 10)

    code = file_read_pat % {'path': sbpath, 'data': data, 'length': len(data)}
    code += wrapper_pat
    return check_profile_internal(logmsg, code, "SUCCESS", user1, pass1, user2, pass2)

def file_write_check(logmsg, sbpath, data=None,
                    user1="test1", pass1="supersecretpassword",
                    user2="test2", pass2="pass",
                    blind_write=False):
    if not data:
        data = b'file_write_check test string'

    code = file_write_pat % {'path': sbpath, 'data': data}
    code += wrapper_pat
    res = check_profile_internal(logmsg, code, "SUCCESS", user1, pass1, user2, pass2)
    if blind_write:
        return True

    if not res:
        print("failed")
        return False

    ok = file_read_check(logmsg + "read and compare:", sbpath, None, data, user1, pass1, user2, pass2)
    return ok

def check_profile(prof_py, prof_pat, msg):
    code = file_read(os.path.join(thisdir, "profiles", prof_py))
    ret = check_profile_internal("%s:" % msg, code, prof_pat)
    if not ret:
        fail("Profile", prof_py, ":", msg)
    return ret

def check_hello():
    pat = "profile.*Hello,.*test2.*Current time: \d+\.\d+"
    if check_profile("hello-user.py", pat, "Hello user check"):
        ok("Profile hello-user.py")

#there has got to be a better way...
def check_myprofile():
    code = file_read(os.path.join(thisdir, "profiles", "my-profile.py"))

    # . is sufficient for matching, since check_profile_internal will already
    # check if the code generates a Traceback, and fail if it does.
    ret = check_profile_internal("Challenge 2: my-profile functional", code, ".")
    if not ret:
        fail("Challenge 2: Profile my-profile doesn't seem to parse correctly")
    else:
        ok("Challenge 2: basic sanity check")


def check_visit_tracker_1():
    pat = "profile.*Hello,.*test2.*Your visit count: 0.*Your last visit: never"
    return check_profile("visit-tracker.py", pat, "First visit check")

def check_visit_tracker_2():
    pat = "profile.*Hello,.*test2.*Your visit count: 1.*Your last visit: \d+\.\d+"
    return check_profile("visit-tracker.py", pat, "Second visit check")

def check_visit_tracker():
    if check_visit_tracker_1() and check_visit_tracker_2():
        ok("Profile visit-tracker.py")

def check_last_visits_1():
    pat = "profile.*Last 3 visitors:.*test2 at \d+"
    return check_profile("last-visits.py", pat, "Last visits check (1/3)")

def check_last_visits_2():
    pat = "profile.*Last 3 visitors:.*test2 at \d+.*test2 at \d+"
    return check_profile("last-visits.py", pat, "Last visits check (2/3)")

def check_last_visits_3():
    pat = "profile.*Last 3 visitors:.*test2 at \d+.*test2 at \d+.*test2 at \d+"
    return check_profile("last-visits.py", pat, "Last visits check (3/3)")

def check_last_visits():
    if check_last_visits_1() and check_last_visits_2() and check_last_visits_3():
        ok("Profile last-visits.py")

def check_xfer_tracker_1():
    now = datetime.datetime.now()
    pat = "profile.*I gave you 3 zoobars \@ .* %d" % now.year
    return check_profile("xfer-tracker.py", pat, "Transfer tracker check")

def check_xfer_tracker():
    if check_xfer_tracker_1():
        ok("Profile xfer-tracker.py")

def check_granter_1():
    pat = "profile.*Thanks for visiting.  I gave you one zoobar."
    if not check_profile("granter.py", pat, "Zoobar grant check"):
        return False

    # check that profile owner token was used and not visitor's, by checking
    # that profile owner has one less zoobar
    html, cookies = z_client.login("test1", "supersecretpassword")
    if not z_client.check_zoobars(html, b"test1", 6, "")[0]:
        fail("Exercises 8-10:", "Not using profile owner's token")

    return True

def check_granter_2():
    pat = "profile.*I gave you a zoobar .* seconds ago"
    return check_profile("granter.py", pat, "'Greedy visitor check1")

def check_granter_3():
    html3, cookies3 = z_client.register("test3", "pass")
    z_client.transfer(cookies3, "test2", 10)
    pat = "profile.*You have \d+ already; no need for more"
    return check_profile("granter.py", pat, "Greedy visitor check2")

def check_granter_4():
    html1, cookies1 = z_client.login("test1", "supersecretpassword")
    z_client.transfer(cookies1, "test2", 6)
    pat = "profile.*Sorry, I have no more zoobars"
    return check_profile("granter.py", pat, "'I am broke' check")

def check_granter():
    if check_granter_1() and check_granter_2() and \
        check_granter_3() and check_granter_4():
        ok("Profile granter.py")

def check_profile_service():
    persondb = "/app/zoobar/db/person/person.db"
    if column_in_table('dynamic', persondb, "person", "profile"):
        fail("Challenge 3:", "person table still has column profile")
        return False
    return True

def check_ex10():
    check_run(["dynamic", "static", "bank", "auth", "profile"])
    check_nodb("profile")
    check_hello()
    check_visit_tracker()
    check_last_visits()
    check_xfer_tracker()
    check_granter()

# check that the file system is separate for different users
def check_fs(tmpfile, blind_write):
    data    = "testfile check test string"

    # write to / as user test1
    if not file_write_check("Exercise 11: %s write:" % tmpfile, tmpfile, data,
                            "test1", "supersecretpassword", "test2", "pass", blind_write=blind_write):
        fail("Exercise 11: test file check (could not write to %s)" % tmpfile)
        return False

    # try to read the same file
    if file_read_check("Exercise 11: shared %s:" % tmpfile, tmpfile, None, data,
                       "test2", "pass", "test1", "supersecretpassword"):
        fail("Exercise 11: test file check (%s shared by more than one user)" % tmpfile)
        return False

    return True

looper_code = '''#!python
while True: pass
'''

def check_looper():
    start = time.time()
    res = check_profile_internal("Exercise 11: infinite loop", looper_code, None)
    end = time.time()
    if end - start < 5:
        fail("Exercise 11:", "Infinite loop returned too fast (%f)" % (end-start))
    if end - start > 20:
        fail("Exercise 11:", "Infinite loop took over 20 seconds to terminate (%f)" % (end-start))
    return True

def check_ex11():
    if check_file("profile", "/tmp/last_visits_test1.dat"):
        fail("Exercise 11:", "Using same pathname that is not user specific")
    if not check_fs("/data/testfile", False):
        return
    if not check_fs("/lib/testfile", True):
        return
    if not check_fs("/testfile", True):
        return
    if not check_looper():
        return
    ok("Exercise 11")

def check_ex12():
    if check_nocomm("static", "dynamic") and check_nocomm("static", "auth") and check_nocomm("main", "auth") and check_nocomm("profile", "auth"):
        ok("Exercise 12 fwrule")

def check_challenge():
    # Challenge 2
    check_myprofile()
    # Challenge 3
    if check_profile_service():
       ok("Challenge: profile column not in person db")

def main():
    if '-v' in sys.argv:
        global verbose
        verbose = True

    try:
        setup()
        check_ex1()
        check_ex2()
        check_ex3()
        check_ex4()
        check_ex5()
        check_ex6()
        check_ex7()
        check_ex8()
        check_ex9()
        check_ex10()
        check_ex11()
        check_ex12()
        killall()
    except Exception:
        log_exit(traceback.format_exc())

if __name__ == "__main__":
    zookconf.restart_with_cgroups()
    main()
