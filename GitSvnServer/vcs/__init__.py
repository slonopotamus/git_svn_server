
import imp as _imp
import os as _os
import sys as _sys

for _fname in _os.listdir(_os.path.dirname(__file__)):
    if _fname.startswith('.') or _fname == '__init__.py':
        continue

    print _fname

    if _fname.endswith('.py'):
        print "py", _fname
        _name = _fname[:-3]
        _cname = _name.title()
        _path = _os.path.join(_os.path.dirname(__file__), _fname)
        globals()[_cname] = _imp.load_source(_name, _path).__dict__[_cname]

    elif _os.path.isdir(_os.path.join(_os.path.dirname(__file__), _fname)):
        print "dir", _fname
        _name = _fname
        _cname = _name.title()
        _sys_path = _sys.path
        _sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), _fname))
        _path = _os.path.join(_os.path.dirname(__file__), _fname, '__init__.py')
        globals()[_cname] = _imp.load_source(_name, _path).__dict__[_cname]
        _sys.path = _sys_path

del _imp, _os, _sys, _sys_path, _fname, _cname, _name, _path
