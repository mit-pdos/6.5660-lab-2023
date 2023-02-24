#!/usr/bin/env python3

import z3 # type: ignore
from typing import Dict

## Construct two 32-bit integer values.  Do not change this code.
a = z3.BitVec('a', 32)
b = z3.BitVec('b', 32)

## Compute the average of a and b.  The initial computation we provided
## naively adds them and divides by two, but that is not correct.  Modify
## these lines to implement your solution for both unsigned (u_avg) and
## signed (s_avg) division.
##
## Watch out for the difference between signed and unsigned integer
## operations.  For example, the Z3 expression (x/2) performs signed
## division, meaning it treats the 32-bit value as a signed integer.
## Similarly, (x>>16) shifts x by 16 bits to the right, treating it
## as a signed integer.
##
## Use z3.UDiv(x, y) for unsigned division of x by y.
## Use z3.LShR(x, y) for unsigned (logical) right shift of x by y bits.
u_avg = z3.UDiv(a + b, 2)
s_avg = (a + b) / 2

## Do not change the code below.

## To compute the reference answers, we extend both a and b by one
## more bit (to 33 bits), add them, divide by two, and shrink back
## down to 32 bits.  You are not allowed to "cheat" in this way in
## your answer.
az33 = z3.ZeroExt(1, a)
bz33 = z3.ZeroExt(1, b)
real_u_avg = z3.Extract(31, 0, z3.UDiv(az33 + bz33, 2))

as33 = z3.SignExt(1, a)
bs33 = z3.SignExt(1, b)
real_s_avg = z3.Extract(31, 0, (as33 + bs33) / 2)

def printable_val(v: z3.BitVecNumRef, signed: bool) -> int:
    if type(v) == z3.BitVecNumRef:
        if signed:
            v = v.as_signed_long()
        else:
            v = v.as_long()
    return v # type: ignore

def printable_model(m: z3.ModelRef, signed: bool) -> Dict[str, int]:
    vals: Dict[str, int] = {}
    for k in m:
        vals[k] = printable_val(m[k], signed)
    return vals

def do_check(msg: str, signed: bool, avg: z3.BitVecRef, real_avg: z3.BitVecRef) -> None:
    e = (avg != real_avg)
    print("Checking", msg, "using Z3 expression:")
    print("    " + str(e).replace("\n", "\n    "))
    solver = z3.Solver()
    solver.add(e)
    ok = solver.check()
    print("  Answer for %s: %s" % (msg, ok))

    if ok == z3.sat:
        m = solver.model()
        print("  Example:", printable_model(m, signed))
        print("  Your average:", printable_val(m.eval(avg), signed))
        print("  Real average:", printable_val(m.eval(real_avg), signed))

do_check("unsigned avg", False, u_avg, real_u_avg)
do_check("signed avg", True, s_avg, real_s_avg)
