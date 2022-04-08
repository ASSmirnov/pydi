from typing import Dict, Type, List, Iterator, Protocol, Any
from ..base import Component, Singleton, Scope
from ..exceptions import ScopeRedeclaration, GroupFactoryNotFound, GroupNotFound


class Factory(Protocol):
    def __call__(self, *args, **kwargs) -> Type:
        ...


class Strategy(Protocol):
    def __call__(self, *args, **kwargs) -> Type:
        ...


class Register(Singleton):
    
    __readonly__ = True

    def __init__(self):
        self.interfaces: Dict[Type, List[Component]] = {}
        self.named_components: Dict[str, Component] = {}
        self.groups: Dict[str, List[Component]] = {}
        self.components: List[Component] = []
        self.strategies: Dict[str, Strategy] = {}
        self.factories: Dict[str, Factory] = {}
        self.scopes: Dict[str, Scope] = {}

    def register_interface(self, interface):
        self.interfaces[interface] = []

    def register_component(self, component: Component):
        self.components.append(component)

    def register_strategy(self, group_name: str, func: Strategy):
        self.strategies[group_name] = func

    def register_factory(self, factory_name: str, func: Factory):
        self.factories[factory_name] = func

    def register_scope(self, name: str, scope: Scope):
        if name in self.scopes:
            raise ScopeRedeclaration(f"Scope {name} already registered")
        self.scopes[name] = scope

    def is_interface(self, cls: Type):
        return cls in self.interfaces

    def get_components(self, interface: Type) -> Iterator[Component]:
        for component in self.interfaces.get(interface, []):
            yield component

    def get_named_component(self, component_name: str) -> Component:
        return self.named_components.get(component_name)

    def get_factory(self, factory_name: str):
        return self.factories.get(factory_name)
    # def get_group_factory(self, group_name: str) -> GroupFactory:
    #     if group_name not in self.groups:
    #         raise GroupNotFound("No group found '{group_name}'")
    #     if group_name not in self.group_factories:
    #         raise GroupFactoryNotFound(f"No group factory found for group {group_name}")
    #     return self.group_factories[group_name]

    def get_group(self, group_name: str) -> List[Component]:
        if group_name not in self.groups:
            raise GroupNotFound(f"No group found '{group_name}'")
        return register.groups[group_name]

    def get_scope(self, scope: str):
        return self.scopes[scope]

register = Register()
