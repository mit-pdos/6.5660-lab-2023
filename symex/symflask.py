## This module wraps the URL-matching code used by flask to be
## friendly to symbolic / concolic execution.

import flask
import werkzeug
from . import fuzzy

## For older versions of Werkzeug (e.g., 2.0.2)
class SymbolicRule(werkzeug.routing.Rule):
  def __init__(self, string, **kwargs):
    super(SymbolicRule, self).__init__(string, **kwargs)
    self.symvarnames = {}
    for converter, arguments, variable in werkzeug.routing.parse_rule(string):
      if converter is 'path':
        self.symvarnames[variable] = fuzzy.uniqname(variable)

  def match(self, path, method=None):
    # print('match', path, method, 'rule', self.rule)
    orig = super(SymbolicRule, self).match(path, method)

    expectpath = "|"
    res = {v: fuzzy.mk_str(n, orig.get(v, '')) for (v, n) in self.symvarnames.items()}
    for converter, arguments, variable in werkzeug.routing.parse_rule(self.rule):
      if arguments is not None:
        return orig
      if converter is None:
        expectpath += variable
      elif converter is 'path':
        expectpath += res[variable]
        if '/' in res[variable]:
          ## nonsensical assignment of concrete value; fall back to orig
          return orig
      else:
        return orig

    if expectpath == path:
      return res
    else:
      return orig

## For newer versions of Werkzeug (e.g., 2.2.3)
class SymbolicMatcher:
  def __init__(self, matcher):
    self._matcher = matcher
    self.rules = []

  def add(self, rule):
    self._matcher.add(rule)
    self.rules.append(rule)

  def update(self):
    self._matcher.update()

  def match(self, domain, path, method, websocket):
    # print("match", domain, path, method, websocket)

    ## Run through the match process to generate path constraints,
    ## but then return the result from the concrete implementation
    ## of the matcher, since we don't need to preserve any symbolic
    ## expressions (we don't support symbolic variables via path).

    for r in self.rules:
      if method not in r.methods:
        continue
      if websocket != r.websocket:
        continue
      parts = r._parts

      ## First match the domain
      if parts[0].content != domain:
        continue

      ## Next, try to match remaining parts against the path.
      path_remaining = path
      for p in parts[1:]:
        if path_remaining is None:
          break
        sp = path_remaining.split('/', 1)
        if len(sp) < 2:
          this = path_remaining
          path_remaining = None
        else:
          this = sp[0]
          path_remaining = sp[1]
        if this != p.content:
          break
      else:
        ## Match, some stuff remaining in path_remaining
        break

    return self._matcher.match(domain, path, method, websocket)

class SymbolicMap(werkzeug.routing.Map):
  def __init__(self, *args, **kwargs):
    super(SymbolicMap, self).__init__(*args, **kwargs)
    if hasattr(self, '_matcher'):
      self._matcher = SymbolicMatcher(self._matcher)

## This works with all versions of Werkzeug
class SymbolicRequest(flask.Request):
  @werkzeug.utils.cached_property
  def cookies(self):
    hdr = self.environ.get('HTTP_COOKIE', '')
    nameval = hdr.split('=', maxsplit=1)
    if len(nameval) < 2:
      return {}
    else:
      (name, val) = nameval
      return {name: val}

  @werkzeug.utils.cached_property
  def form(self):
    ## Maybe make a concolic_dict() that would eliminate the need
    ## to enumerate all the keys of interest here?
    res = {}
    for k in ('recipient', 'zoobars'):
      if fuzzy.mk_int('form_%s_present' % k, 0) == 0:
        continue
      res[k] = fuzzy.mk_str('form_%s_val' % k, '')
    return res

flask.Flask.request_class = SymbolicRequest
match werkzeug.__version__:
  case '2.2.3':
    flask.Flask.url_map_class = SymbolicMap
  case '2.0.2':
    flask.Flask.url_rule_class = SymbolicRule
  case _:
    raise Exception('unclear how to handle werkzeug version %s' % werkzeug.__version__)
