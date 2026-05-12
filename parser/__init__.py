"""
Shim для distutils.version — он удалён из stdlib в Python 3.12,
а undetected_chromedriver 3.5.5 импортирует оттуда LooseVersion.
Подгружается до import undetected_chromedriver в dodo_parser.py.
"""
import re
import sys
import types


def _install_distutils_shim() -> None:
    if "distutils.version" in sys.modules:
        return
    try:
        from distutils.version import LooseVersion  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    class LooseVersion:
        def __init__(self, vstring):
            self.vstring = str(vstring)
            self.version = tuple(int(x) for x in re.findall(r"\d+", self.vstring))

        def _other(self, o):
            return o.version if isinstance(o, LooseVersion) else LooseVersion(o).version

        def __lt__(self, o): return self.version < self._other(o)
        def __le__(self, o): return self.version <= self._other(o)
        def __gt__(self, o): return self.version > self._other(o)
        def __ge__(self, o): return self.version >= self._other(o)
        def __eq__(self, o): return self.version == self._other(o)
        def __ne__(self, o): return self.version != self._other(o)
        def __hash__(self): return hash(self.version)
        def __repr__(self): return f"LooseVersion('{self.vstring}')"
        def __str__(self): return self.vstring

    version_mod = types.ModuleType("distutils.version")
    version_mod.LooseVersion = LooseVersion
    distutils_mod = types.ModuleType("distutils")
    distutils_mod.version = version_mod
    sys.modules["distutils"] = distutils_mod
    sys.modules["distutils.version"] = version_mod


_install_distutils_shim()
