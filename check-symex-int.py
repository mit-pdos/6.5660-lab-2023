#!/usr/bin/env python3

import symex.fuzzy as fuzzy
import symex_exercises
import z3 # type: ignore

def f(x: int) -> int:
    if x == 7:
        return 100
    if x*2 == x+1:
        return 70
    if x > 2000:
        return 80
    if x*2 == 1000:
        return 30000
    if x < 500:
        return 33
    if x // 123 == 7:
        return 1234
    return 40

def test_f() -> int:
    i = fuzzy.mk_int('i', 0)
    v = f(i)
    return v

## This test case checks that you provided the right input in symex_exercises.
print('Calling f with a specific input..')
v = symex_exercises.make_a_test_case()
(r, constr_callers) = fuzzy.concolic_exec_input(test_f, v, verbose=1)
if r == 1234:
    print("Found input for 1234")
else:
    print("Input produced", r, "instead of 1234")

## This test case provides one check for concolic_find_input()
print('Find input')
a = fuzzy.sym_int('a')
b = fuzzy.sym_int('b')
c = fuzzy.sym_int('c')
constr2 = fuzzy.sym_and(
    fuzzy.sym_eq(a, fuzzy.const_int(5)),
    fuzzy.sym_lt(b, fuzzy.const_int(10)),
    fuzzy.sym_lt(fuzzy.const_int(3), b),
    fuzzy.sym_eq(fuzzy.sym_plus(a, b), fuzzy.const_int(12)),
    fuzzy.sym_eq(c, fuzzy.const_int(1)))
(ok2, v2) = fuzzy.concolic_find_input(constr2, ['a', 'b'], verbose=1)
if ok2:
    if v2.canonical_rep() == [('a', 5), ('b', 7)]:
        print("Found correct input for constr2")
    else:
        print("Incorrect input for constr2")
else:
    print("Could not find input for constr2")

constr3 = fuzzy.sym_and(constr2, fuzzy.sym_gt(a, fuzzy.const_int(7)))
(ok3, v3) = fuzzy.concolic_find_input(constr3, ['a', 'b'], verbose=1)
if ok3:
    print("Erroneously found input for constr3")
else:
    print("Correctly found no input for constr3")


## This test case constructs a hypothetical set of branches
## where the program first checks (a == 5), then checks (b < 10),
## etc, as shown in the test_branches array below.  Then, we use
## concolic_force_branch() to generate constraints for forcing the
## execution to take an alternate branch at every one of these
## branch points.

print('Force branch')

test_branches: list[fuzzy.sym_ast] = [
    ( fuzzy.sym_eq(a, fuzzy.const_int(5)),
      ('dummy.py', 1) ),
    ( fuzzy.sym_lt(b, fuzzy.const_int(10)),
      ('dummy.py', 2) ),
    ( fuzzy.sym_lt(fuzzy.const_int(3), b),
      ('dummy.py', 3) ),
    ( fuzzy.sym_eq(fuzzy.sym_plus(a, b), fuzzy.const_int(12)),
      ('dummy.py', 4) ),
    ( fuzzy.sym_eq(c, fuzzy.const_int(1)),
      ('dummy.py', 5) ),
    ( fuzzy.sym_eq(c, fuzzy.const_int(2)),
      ('dummy.py', 6) ),
]

all_ok = True
for i in range(0, 6):
    bconstr = fuzzy.concolic_force_branch(i, test_branches, verbose=3)
    for j in range(0, i):
        (ok, _) = fuzzy.fork_and_check(fuzzy.sym_and(bconstr, fuzzy.sym_not(test_branches[j][0])))
        if ok == z3.sat:
            print("Incorrect constraint [1] for forcing branch", i)
            all_ok = False
    (ok, _) = fuzzy.fork_and_check(fuzzy.sym_and(bconstr, test_branches[i][0]))
    if ok == z3.sat:
        print("Incorrect constraint [2] for forcing branch", i)
        all_ok = False
if all_ok:
    print("Correct implementation of concolic_force_branch")


print('Testing f..')
f_results = fuzzy.concolic_execs(test_f, verbose=1)

f_expected = (100, 70, 80, 33, 1234, 40)
if all(x in f_results for x in f_expected):
    print("Found all cases for f")
else:
    print("Missing some cases for f:", set(f_expected) - set(f_results))
