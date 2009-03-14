
import imp as _imp
import os as _os

for _fname in _os.listdir(_os.path.dirname(__file__)):
    if _fname.startswith('.') or _fname == '__init__.py':
        continue

    if _fname.endswith('.py'):
        _name = _fname[:-3]
        _cname = _name.replace('-', '_')
        _path = _os.path.join(_os.path.dirname(__file__), _fname)
        globals()[_cname] = _imp.load_source(_name, _path)

del _imp, _os, _fname, _cname, _name, _path
