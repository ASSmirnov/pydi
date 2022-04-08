from typing import Any, Optional, Type

from .core._runtime import scope as _scope
from .core._runtime.scope import SingletonScope, PrototypeScope
from .core.exceptions import AlreadyStarted, NotStarted
from .core._runtime.config import config as _config
from .core._build.builder import builder as _builder
from .core._prepare.register import register as _register
from .core._runtime.context import context as _context
from .core.base import Singleton as _Singleton
from .core.base import Lazy, Volatile, Group
from .core.decorators import component, interface, strategy, factory

_started = False
_configured = False


def configure(*, active_environ="prod", default_environ="prod"):
    global _configured
    if _started:
        raise AlreadyStarted
    _configured = True
    _config.active_environ = active_environ
    _config.default_environ = default_environ


def add_file_config(filename: str):
    pass


def start():
    global context
    global _started
    if not _configured:
        configure()
    _builder._context = _context
    _builder._config = _config
    _builder.build()
    _builder.finalize()
    _config.finalize()
    _register.finalize()
    context = Context()
    context._context = _context
    print(f"{context._context=}")
    _started = True  


class Context(_Singleton):
    def __init__(self):
        if hasattr(self, "_context"):
            return
        self._context = None
    
    def get_instance(self, *,
                     interface: Optional[Type] = None,
                     name: Optional[str] = None,
                     group: Optional[str] = None,
                     **kwargs) -> Any:
        return self._context.get_instance(interface, name, group, **kwargs)

    def get_instances(self, *,
                      interface: Optional[Type] = None,
                      group: Optional[str] = None):
        for instance in self._context.get_instances(interface, group):
            yield instance

def get_context():
    if not _started:
        raise NotStarted
    return Context()
