#!/usr/bin/env python3

import os
import sys
import time
import subprocess
import traceback
from stat import *

os.environ['SQLALCHEMY_SILENCE_UBER_WARNING'] = '1'

thisdir = os.path.dirname(os.path.abspath(__file__))
verbose = False

def green(s):
    return '\033[1;32m%s\033[m' % s

def red(s):
    return '\033[1;31m%s\033[m' % s

def log(*m):
    print(" ".join(m), file=sys.stderr)

def log_exit(*m):
    log(red("ERROR:"), *m)
    exit(1)

def file_read(pn):
    with open(pn) as fp:
        return fp.read()

def sh(cmd, exit_onerr=True):
    if verbose: log("+", cmd)
    if os.system(cmd) != 0 and exit_onerr:
        log_exit("running shell command:", cmd)

def check_intavg():
    sh('python3 int-avg.py >/tmp/lab3.log')
    if 'Answer for unsigned avg: unsat' in file_read('/tmp/lab3.log'):
        log(green("PASS"), "Exercise 1: unsigned average")
    else:
        log(red("FAIL"), "Exercise 1: unsigned average")
    if 'Answer for signed avg: unsat' in file_read('/tmp/lab3.log'):
        log(green("PASS"), "Challenge 1: signed average")
    else:
        log(red("FAIL"), "Challenge 1: signed average")

def check_concolic_int():
    sh('python3 check-concolic-int.py >/tmp/lab3.log')
    if 'Multiply works' in file_read('/tmp/lab3.log'):
        log(green("PASS"), "Exercise 2: concolic multiply")
    else:
        log(red("FAIL"), "Exercise 2: concolic multiply")
    if 'Divide works' in file_read('/tmp/lab3.log'):
        log(green("PASS"), "Exercise 2: concolic divide")
    else:
        log(red("FAIL"), "Exercise 2: concolic divide")
    if 'Divide+multiply+add works' in file_read('/tmp/lab3.log'):
        log(green("PASS"), "Exercise 2: concolic divide+multiply+add")
    else:
        log(red("FAIL"), "Exercise 2: concolic divide+multiply+add")

def check_symex_int():
    sh('python3 check-symex-int.py >/tmp/lab3.log')
    if 'Found input for 1234' in file_read('/tmp/lab3.log'):
        log(green("PASS"), "Exercise 3: concrete input for 1234")
    else:
        log(red("FAIL"), "Exercise 3: concrete input for 1234")

    if 'Found correct input for constr2' in file_read('/tmp/lab3.log'):
        log(green("PASS"), "Exercise 4: concolic_find_input constr2")
    else:
        log(red("FAIL"), "Exercise 4: concolic_find_input constr2")

    if 'Correctly found no input for constr3' in file_read('/tmp/lab3.log'):
        log(green("PASS"), "Exercise 4: concolic_find_input constr3")
    else:
        log(red("FAIL"), "Exercise 4: concolic_find_input constr3")

    if 'Correct implementation of concolic_force_branch' in file_read('/tmp/lab3.log'):
        log(green("PASS"), "Exercise 5: concolic_force_branch")
    else:
        log(red("FAIL"), "Exercise 5: concolic_force_branch")

    if 'Found all cases for f' in file_read('/tmp/lab3.log'):
        log(green("PASS"), "Exercise 6: concolic execution for integers")
    else:
        log(red("FAIL"), "Exercise 6: concolic execution for integers")

def check_concolic_str():
    sh('python3 check-concolic-str.py >/tmp/lab3.log')
    if 'Length works' in file_read('/tmp/lab3.log'):
        log(green("PASS"), "Exercise 7: concolic length")
    else:
        log(red("FAIL"), "Exercise 7: concolic length")
    if 'Contains works' in file_read('/tmp/lab3.log'):
        log(green("PASS"), "Exercise 7: concolic contains")
    else:
        log(red("FAIL"), "Exercise 7: concolic contains")

def check_symex_str():
    sh('python3 check-symex-str.py >/tmp/lab3.log')
    if 'Found all cases for g' in file_read('/tmp/lab3.log'):
        log(green("PASS"), "Exercise 7: concolic execution for strings")
    else:
        log(red("FAIL"), "Exercise 7: concolic execution for strings")

def check_symex_sql():
    sh('python3 check-symex-sql.py >/tmp/lab3.log')
    if 'Found all cases for f' in file_read('/tmp/lab3.log'):
        log(green("PASS"), "Exercise 8: concolic database lookup (str)")
    else:
        log(red("FAIL"), "Exercise 8: concolic database lookup (str)")
    if 'Found all cases for g' in file_read('/tmp/lab3.log'):
        log(green("PASS"), "Exercise 8: concolic database lookup (int)")
    else:
        log(red("FAIL"), "Exercise 8: concolic database lookup (int)")

def check_symex_zoobar():
    sh('python3 check-symex-zoobar.py >/tmp/lab3.log 2>&1')
    if 'Exception: eval injection' in file_read('/tmp/lab3.log'):
        log(green("PASS"), "Exercise 9: eval injection found")
    else:
        log(red("FAIL"), "Exercise 9: eval injection not found")
    if 'WARNING: Balance mismatch detected' in file_read('/tmp/lab3.log'):
        log(green("PASS"), "Exercise 9: balance mismatch found")
    else:
        log(red("FAIL"), "Exercise 9: balance mismatch not found")
    if 'WARNING: Zoobar theft detected' in file_read('/tmp/lab3.log'):
        log(green("PASS"), "Exercise 9: zoobar theft found")
    else:
        log(red("FAIL"), "Exercise 9: zoobar theft not found")

def check_symex_zoobar_fixed():
    sh('sh check-symex-zoobar-fixed.sh >/tmp/lab3.log 2>&1')
    if 'Exception: eval injection' in file_read('/tmp/lab3.log'):
        log(red("FAIL"), "Exercise 10: eval injection still found")
    else:
        log(green("PASS"), "Exercise 10: eval injection not found")
    if 'WARNING: Balance mismatch detected' in file_read('/tmp/lab3.log'):
        log(red("FAIL"), "Exercise 10: balance mismatch still found")
    else:
        log(green("PASS"), "Exercise 10: balance mismatch not found")
    if 'WARNING: Zoobar theft detected' in file_read('/tmp/lab3.log'):
        log(red("FAIL"), "Exercise 10: zoobar theft still found")
    else:
        log(green("PASS"), "Exercise 10: zoobar theft not found")

def main():
    if '-v' in sys.argv:
        global verbose
        verbose = True

    try:
        check_intavg()
        check_concolic_int()
        check_symex_int()
        check_concolic_str()
        check_symex_str()
        check_symex_sql()
        check_symex_zoobar()
        check_symex_zoobar_fixed()
    except Exception:
        log_exit(traceback.format_exc())

if __name__ == "__main__":
    main()
