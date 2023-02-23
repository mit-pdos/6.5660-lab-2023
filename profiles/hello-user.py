#!python
import time
import api
print('Hello, <i>', api.call('get_visitor'), '</i>')
print('<p>Current time:', time.time())
