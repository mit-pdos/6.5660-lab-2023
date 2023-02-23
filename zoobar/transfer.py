from flask import g, render_template, request

from login import requirelogin
from zoodb import *
from debug import *
import bank
import traceback
import time

@catch_err
@requirelogin
def transfer():
    # This helps with grading lab 2 exercise 8; you must keep
    # this code at the beginning of the transfer method.
    if 'delay' in request.form:
        time.sleep(int(request.form['delay']))

    warning = None
    try:
        if 'recipient' in request.form:
            zoobars = eval(request.form['zoobars'])
            bank.transfer(g.user.person.username,
                          request.form['recipient'], zoobars)
            warning = "Sent %d zoobars" % zoobars
    except (KeyError, ValueError, AttributeError) as e:
        traceback.print_exc()
        warning = "Transfer to %s failed" % request.form['recipient']

    return render_template('transfer.html', warning=warning)
