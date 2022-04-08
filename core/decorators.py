from typing import _ProtocolMeta, Union, List, Type, Optional
from .base import Component, ALL
from .exceptions import ImproperlyConfigured
from ._prepare.register import register


def interface(cls: Type):
    if type(cls) != _ProtocolMeta:
        raise ImproperlyConfigured("Only classes deriving Protocol can be decorated as interface")
    register.register_interface(cls)
    return cls


current_uid = 0


def component(implements: Union[List[Type], Type],
              scope: str,
              name: Optional[str] = None,
              environ: Union[None, str, List[str]] = None,
              group: Optional[str] = None,  # TODO list of group,
              factory_name: Optional[str] = None
              ):

    if not isinstance(implements, list):
        implements = [implements]

    if environ:
        if isinstance(environ, str):
            environ = {environ}
        elif isinstance(environ, (list, tuple, set)):
            environ = set(environ)
        else:
            raise ImproperlyConfigured(f"Environ must be list[str], set[str], tuple[str] or str, {environ} given")
        if ALL in environ:
            environ = {ALL}

    def wrapper(cls):
        if type(cls) != type:
            raise ImproperlyConfigured("Only classes can be decorated as interface")

        for i in implements:
            if not register.is_interface(i):
                raise ImproperlyConfigured(f"Component {cls} implements unknown interface {i}")

        global current_uid
        current_uid += 1
        comp = Component(cls=cls,
                         uid=current_uid,
                         implements=implements,
                         scope=scope,
                         name=name,
                         environ=environ,
                         group=group,
                         factory_name=factory_name)
        register.register_component(comp)
        return cls

    return wrapper


def strategy(group_name: str):

    def wrapper(func):
        register.register_strategy(group_name, func)
        return func
    return wrapper


def factory(factory_name: str):

    def wrapper(func):
        register.register_factory(factory_name, func)
        return func
    return wrapper
