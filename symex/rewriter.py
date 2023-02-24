import inspect
import types
import builtins
import bytecode

def __rewriter_pct(a, b):
  orig = a % b
  origa = a
  origb = b
  if isinstance(a, str):
    res = ''
    while True:
      pos = a.find('%')
      if pos < 0:
        # if res+a != orig: print('__rewriter_pct mismatch:', res+a, orig)
        return res + a
      res += a[0:pos]
      a = a[pos:]
      if a[1] == 's':
        if isinstance(b, tuple):
          v = b[0]
          b = b[1:]
        else:
          v = b
        res = res + str(v)
        a = a[2:]
      elif a[1] == '(':
        pos = a.find(')')
        if pos < 0:
          break
        name = a[2:pos]
        if a[pos+1] != 's':
          break
        res += str(b[name])
        a = a[pos+2:]
      else:
        break

    ## couldn't figure out this pattern..
    # print("__rewriter_pct: bailing out on pattern", origa)
    return orig
  else:
    return orig

def __rewriter_contains(a, b):
  if not isinstance(b, dict) and \
     not isinstance(b, set) and \
     not isinstance(b, list) and \
     not isinstance(b, tuple):
    return a in b

  if a is None:
    return any(k is None for k in b)
  else:
    return any(a == k for k in b)

def __rewriter_not_contains(a, b):
  return not __rewriter_contains(a, b)

def __newget(x, b, default = None):
  for (k, v) in x.items():
    if b == k:
      return v
  return default

def __rewriter_load_attr_get(a):
  ## override 'get' for dicts
  ##
  ## isinstance(a, dict) is not sufficient because a class
  ## can subclass dict but can override the get() function

  ## return unbound function for dict.get
  if a is dict:
    return __newget

  for cls in inspect.getmro(type(a)):
    ## rewrite for dict and dictproxy
    if cls == dict:
      break

    ## check for non-dict "get" method
    for (name, v) in inspect.getmembers(cls):
      if name == "get" and v == dict.get:
        break
      elif name == "get":
        ## return found function bound to 'a'
        return v.__get__(a)

  return __newget.__get__(a)

def __rewriter_load_method_get(a, *args, **kwargs):
  ## override 'get' for dicts
  ##
  ## isinstance(a, dict) is not sufficient because a class
  ## can subclass dict but can override the get() function

  ## invoke the function for dict.get
  if a is dict:
    return __newget(*args, **kwargs)

  for cls in inspect.getmro(type(a)):
    ## rewrite for dict and dictproxy
    if cls == dict:
      break

    ## check for non-dict "get" method
    for (name, v) in inspect.getmembers(cls):
      if name == "get" and v == dict.get:
        break
      elif name == "get":
        ## invoke found function
        return v(a, *args, **kwargs)

  return __newget(a, *args, **kwargs)

def __rewriter_eq(a, b):
  return a == b

def __rewriter_concat(l):
  res = ''
  for x in l:
    res = res + x
  return res

## Stick our replacement functions into the builtins module
## so they are in the namespace of any function we're rewriting.
builtins.__rewriter_pct = __rewriter_pct
builtins.__rewriter_contains = __rewriter_contains
builtins.__rewriter_not_contains = __rewriter_not_contains
builtins.__rewriter_load_attr_get = __rewriter_load_attr_get
builtins.__rewriter_load_method_get = __rewriter_load_method_get
builtins.__rewriter_eq = __rewriter_eq
builtins.__rewriter_concat = __rewriter_concat

def rewrite_function(f):
  if hasattr(f, '__code_rewrite_done__'):
    return
  f.__code_rewrite_done__ = None

  if not hasattr(f, '__code__'):
    return
  bc = bytecode.Bytecode.from_code(f.__code__)

  newinstr, changed = rewrite_bytecode(bc)
  if not changed:
    return

  bc.clear()
  bc.extend(newinstr)
  c = bc.to_code()
  f.__code__ = c
  return

def rewrite_bytecode(bc):
  newinstr = []
  changed = False

  for i in bc:
    if isinstance(i, bytecode.Label):
      newinstr.append(i)
      continue

    if i.name == 'BINARY_MODULO':
      newinstr.append(bytecode.Instr("LOAD_GLOBAL", "__rewriter_pct"))
      newinstr.append(bytecode.Instr("ROT_THREE"))
      newinstr.append(bytecode.Instr("CALL_FUNCTION", 2))
      changed = True
      continue

    if i.name == 'CONTAINS_OP' and i.arg == 0:
      newinstr.append(bytecode.Instr("LOAD_GLOBAL", "__rewriter_contains"))
      newinstr.append(bytecode.Instr("ROT_THREE"))
      newinstr.append(bytecode.Instr("CALL_FUNCTION", 2))
      changed = True
      continue

    if i.name == 'CONTAINS_OP' and i.arg != 0:
      newinstr.append(bytecode.Instr("LOAD_GLOBAL", "__rewriter_not_contains"))
      newinstr.append(bytecode.Instr("ROT_THREE"))
      newinstr.append(bytecode.Instr("CALL_FUNCTION", 2))
      changed = True
      continue

    if i.name == 'COMPARE_OP' and i.arg == bytecode.Compare.EQ:
      newinstr.append(bytecode.Instr("LOAD_GLOBAL", "__rewriter_eq"))
      newinstr.append(bytecode.Instr("ROT_THREE"))
      newinstr.append(bytecode.Instr("CALL_FUNCTION", 2))
      changed = True
      continue

    if i.name == 'LOAD_ATTR' and i.arg == 'get':
      newinstr.append(bytecode.Instr("LOAD_GLOBAL", "__rewriter_load_attr_get"))
      newinstr.append(bytecode.Instr("ROT_TWO"))
      newinstr.append(bytecode.Instr("CALL_FUNCTION", 1))
      changed = True
      continue

    if i.name == 'LOAD_METHOD' and i.arg == 'get':
      newinstr.append(bytecode.Instr("LOAD_GLOBAL", "__rewriter_load_method_get"))
      newinstr.append(bytecode.Instr("ROT_TWO"))
      changed = True
      continue

    ## Undo the BUILD_STRING optimization (https://bugs.python.org/issue27078)
    ## to preserve symbolic strings.
    if i.name == 'BUILD_STRING':
      newinstr.append(bytecode.Instr("BUILD_LIST", i.arg))
      newinstr.append(bytecode.Instr("LOAD_GLOBAL", "__rewriter_concat"))
      newinstr.append(bytecode.Instr("ROT_TWO"))
      newinstr.append(bytecode.Instr("CALL_FUNCTION", 1))
      changed = True
      continue

    newinstr.append(i)
  return newinstr, changed

def rewriter(m, doneset=None):
  if doneset is None:
    doneset = set()
  if m in doneset:
    return
  doneset.add(m)
  # print('rewriting', m)
  for k in tuple(getattr(m, '__dict__', ()).keys()) + tuple(getattr(m, '__slots__', ())):
    if k.startswith('__') and k.endswith('__'):
      continue
    try:
      v = getattr(m, k)
    except AttributeError:
      ## SQLalchemy has some attributes backed by a getter that
      ## can throw an exception..
      continue
    if type(v) == types.FunctionType:
      rewrite_function(v)
    elif type(v) == types.MethodType:
      rewrite_function(v.__func__)
    elif type(v) == type:
      rewriter(v, doneset)
    elif 'werkzeug.utils.cached_property' in str(type(v)):
      ## XXX what a hack!  we should really do the rewriting earlier,
      ## perhaps when the code is first loaded by Python.  but it's
      ## not clear how to do that..
      rewriter(v, doneset)
    elif type(v) in (str, dict, bool, int, float, bytes, property):
      pass
    elif type(v) in (types.BuiltinFunctionType,):
      pass
    else:
      # print("Not rewriting", k, "type", type(v))
      pass
