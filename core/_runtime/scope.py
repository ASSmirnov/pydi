from typing import Any

from ..base import Scope, Component
from ..exceptions import ScopeIsNotActive, SingletonError
from .._prepare.register import register


class BaseScope(Scope):

    def __init__(self):
        self._active = False

    def enter(self):
        self._active = True

    def exit(self):
        self._active = False

    def _get_instance(self, component: Component, **kwargs):
        if component.factory_name:
            factory = register.get_factory(component.factory_name)
            if factory:
                return factory(component.cls, **kwargs)
        return component.cls(**kwargs)

    def get_instance(self, component: Component, **kwargs):
        if not self._active:
            raise ScopeIsNotActive()
        instance = self._get_instance(component, **kwargs)
        return instance


class SingletonScope(BaseScope):

    def __init__(self):
        super().__init__()
        self._cache = {}

    def get_instance(self, component: Component, **kwargs):
        if kwargs:
            raise SingletonError("Singleton scope does not accept additional arguments")
        if (uid := component.uid) in self._cache:
            return self._cache[uid]
        instance = super().get_instance(component)
        self._cache[uid] = instance
        return instance


class PrototypeScope(BaseScope):

    def get_instance(self, component: Component, **kwargs):
        return super().get_instance(component, **kwargs)


_singletonScope = SingletonScope()
_singletonScope.enter()
register.register_scope("singleton", _singletonScope)

_prototypeScope = PrototypeScope()
_prototypeScope.enter()
register.register_scope("prototype", _prototypeScope)
