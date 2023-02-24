import importlib
import sys

class RewriteLoader(object):
  def __init__(self, base_loader, rewriter):
    self.base_loader = base_loader
    self.rewriter = rewriter

  def create_module(self, spec):
    return self.base_loader.create_module(spec)

  def exec_module(self, module):
    self.base_loader.exec_module(module)
    self.rewriter(module)

  def load_module(self, fullname):
    m = self.base_loader.load_module(fullname)
    self.rewriter(m)
    return m

  def module_repr(self, module):
    return self.base_loader.module_repr(module)

  def is_package(self, fullname):
    return self.base_loader.is_package(fullname)

  def get_code(self, fullname):
    return self.base_loader.get_code(fullname)

class RewriteFinder(object):
  def __init__(self, base_finder, rewriter):
    self.base_finder = base_finder
    self.rewriter = rewriter
    if hasattr(base_finder, 'find_spec'):
      self.find_spec = self._find_spec
    if hasattr(base_finder, 'find_module'):
      self.find_module = self._find_module
    if hasattr(base_finder, 'invalidate_caches'):
      self.invalidate_caches = self._invalidate_caches

  def _find_spec(self, fullname, path, target=None):
    s = self.base_finder.find_spec(fullname, path, target)
    if s is None:
      return s

    rs = importlib.machinery.ModuleSpec(s.name, RewriteLoader(s.loader, self.rewriter))
    rs.origin = s.origin
    rs.loader_state = s.loader_state
    rs.submodule_search_locations = s.submodule_search_locations
    rs.cached = s.cached
    rs.has_location = s.has_location
    return rs

  def _find_module(self, fullname, path):
    l = self.base_finder.find_module(fullname, path)
    if l is None:
      return l

    return RewriterLoader(l, self.rewriter)

  def _invalidate_caches(self):
    return self.base_finder.invalidate_caches()

def rewrite_imports(rewriter):
  sys.meta_path = [RewriteFinder(base_finder, rewriter) for base_finder in sys.meta_path]
