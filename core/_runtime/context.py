from typing import Type, Any, Iterator, Optional

from ..base import Singleton, Component
from .._prepare.register import register
from ..exceptions import (NoCandidatesFound, WrongInstantiating, MoreThanOneCandidateFound,
                          IllegalContextCall)


class _Injector(Singleton):

    def inject(self, component, instance):
        for dependency, descriptor in component.dependencies.values():
            if dependency.inject_immidiately:
                if dependency.group:
                    value = dependency.collection(context.get_instances(group=dependency.group)) 
                elif dependency.collection:
                    value = dependency.collection(context.get_instances(interface=dependency.interface))
                else:
                    value = self.get_instance(dependency.interface)
                descriptor.inject(instance, value)


class Context(Singleton):
    def __init__(self, injector):
        if hasattr(self, "injector"):
            return
        self.injector = injector

    def get_components(self,
                       interface: Optional[Type] = None,
                       group: Optional[str] = None) -> Iterator[Component]:
        if interface and group:
            raise IllegalContextCall("Either interface or group must be passed")
        if interface:
            if not register.is_interface(interface):
                raise WrongInstantiating(f"{interface} is not a registered interface")
            yield from register.get_components(interface)
        elif group:
            yield from register.get_group(group)
        else:
            raise IllegalContextCall("Either interface or group must be passed but not both")

    def get_component(self,
                      interface: Optional[Type] = None,
                      name: Optional[str] = None,
                      group: Optional[str] = None) -> Component:

        if name:
            component = register.get_named_component(name)
            if not component:
                raise NoCandidatesFound(f"No components found for name {name}")
            return component

        components = list(self.get_components(interface, group))
        if not components:
            raise NoCandidatesFound(f"No components found for {'interface' if interface else 'group'} "
                                    f"{interface or group}")

        # if group: # todo rename
        #     factory = register.get_group_factory(group)
        #     components = factory(components)

        if len(components) > 1:
            raise MoreThanOneCandidateFound(f"A number of components found for request "
                                            f"{interface=}, {name=}, {group=} and active. "
                                            f"{[c.cls for c in components]}")
        return components[0]


    def _get_instance(self, component: Component, **kwargs):
        scope = register.get_scope(component.scope)
        instance = scope.get_instance(component, **kwargs)
        self.injector.inject(component, instance)
        return instance

    def get_instance(self,
                     interface: Optional[Type] = None,
                     name: Optional[str] = None,
                     group: Optional[str] = None,
                     **kwargs) -> Any:
        component = self.get_component(interface, name, group)
        return self._get_instance(component, **kwargs)

    def get_instances(self,
                      interface: Optional[Type] = None,
                      group: Optional[str] = None,
                      **kwargs):
        components = self.get_components(interface=interface, group=group)
        for component in components:
            yield self._get_instance(component, **kwargs)


context = Context(_Injector())
