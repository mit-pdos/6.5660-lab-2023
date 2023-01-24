#!/usr/bin/env python3

import subprocess
import re
from typing import List, Tuple

wget_log = []
serverip = "10.1.0.4"

def file_read(pn: str) -> str:
    with open(pn) as fp:
        return fp.read()

def file_write(pn: str, data: str) -> None:
    with open(pn, "w") as fp:
        fp.write(data)

def run_wget(opts: List[str] = []) -> bytes:
    args = list(opts)
    args.insert(0, "wget")
    args.extend(["-O", "-"])
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.wait() != 0:
        raise Exception("wget failed: %s" % p.stderr.read().decode('utf-8', 'ignore')) # type: ignore
    result = p.stdout.read() # type: ignore

    global wget_log
    wget_log.append((args, result))

    return result

def print_wget_log() -> None:
    global wget_log
    for args, result in wget_log:
        print('---')
        print('Request:', args)
        print('Response:')
        # Omit blank lines from result
        for line in result.split(b'\n'):
            if line.strip() != b'':
                print('  %s' % line.decode('utf-8', 'ignore'))

def login_page(op: str, user: str, password: str) -> Tuple[bytes, str]:
    postdata = "login_username=" + user + "&login_password=" + password + \
               "&nexturl=%2Fzoobar%2Findex.cgi%2F&" + \
               ("submit_registration=Register" if op == "register" else "submit_login=Log+in")
    r = run_wget(["http://%s:8080/zoobar/index.cgi/login" % serverip,
                  "--save-cookies", "/tmp/cookies.txt", "--post-data",
                  postdata, "--keep-session-cookies"])
    
    return r, file_read("/tmp/cookies.txt")

def register(user: str, password: str) -> Tuple[bytes, str]:
    return login_page("register", user, password)

def login(user: str, password: str) -> Tuple[bytes, str]:
    return login_page("login", user, password)

def get(url: str, cookies: str) -> bytes:
    file_write("/tmp/cookies.txt", cookies)
    return run_wget([url, "--load-cookies", "/tmp/cookies.txt"])

def post(url: str, cookies: str, postdata: str) -> bytes:
    file_write("/tmp/cookies.txt", cookies)
    return run_wget([url, "--load-cookies", "/tmp/cookies.txt", "--post-data", postdata])

# sender must already be logged in
def transfer(sender_cookies: str, recipient: str, zoobars: int) -> bytes:
    p = "recipient=%s&zoobars=%s&submission=Send" % (recipient, str(zoobars))
    return post("http://%s:8080/zoobar/index.cgi/transfer" % serverip,
                sender_cookies, p)

def view_user(cookies: str, username: str) -> bytes:
    return get(("http://%s:8080/zoobar/index.cgi/users?user=" % serverip) + username, cookies)

def check_zoobars(html: bytes, user: bytes, zoobars: int, zmsg: str) -> Tuple[bool, str]:
    b = str(zoobars).encode()
    if html.find(b"Log out %s" % user) < 0:
        return False, "error fetching user page"
    if re.search(b"Balance.*%s zoobars" % b, html) is None:
        return False, zmsg
    return True, "success"
    
def check(ip: str) -> Tuple[bool, str]:
    # create users test1 and test2
    # check zoobars are initialized to 10
    global serverip
    serverip = ip
    html1, cookies1 = register("test1", "supersecretpassword")
    html2, cookies2 = register("test2", "pass")
    x = check_zoobars(html1, b"test1", 10, "zoobars not initialized to 10")
    if not x[0]:
        print_wget_log()
        return x

    # transfer 3 zoobars from test1 to test2
    # check (i) transfer success (ii) test1 zoobars are 7
    thtml = transfer(cookies1, "test2", 3)
    html1, cookies1 = login("test1", "supersecretpassword")
    x = check_zoobars(html1, b"test1", 7, "invalid sender zoobars after transfer")
    if not x[0]:
        print_wget_log()
        return x

    # login as test2. check zoobars are 13
    html2, cookies2 = login("test2", "pass")
    x = check_zoobars(html2, b"test2", 13, "invalid recipient zoobars after transfer")
    if not x[0]:
        print_wget_log()
        return x

    # view user test1 profile. check zoobars are 7
    vhtml = view_user(cookies2, "test1")
    if vhtml.find(b'<span id="zoobars" class="7">') < 0:
        print_wget_log()
        return False, "invalid sender zoobars after transfer and view user"
    if re.search(b'<table class="log".*test1.*test2.*3', vhtml, re.DOTALL) is None:
        print_wget_log()
        return False, "transfer log not updated after transfer"

    return True, "success"
