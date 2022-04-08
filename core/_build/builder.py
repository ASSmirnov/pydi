from abc import ABC, abstractmethod, abstractproperty
import collections
from functools import cached_property
from typing import ForwardRef, List, Set, Tuple, get_origin, get_args, Any, Type

from ..base import Group, Lazy, Singleton, Component, Dependency, ALL, Volatile
from .._prepare.register import register
from ..exceptions import  ImproperlyConfigured, MoreThanOneCandidateFound, InconsistentGroup, ScopeNotFound, NoCandidatesFound, \
    AttributeWasNotInjected


class BaseDependency:

    def __init__(self, name: str, dependency: Dependency, context): # TODO context protocol
        self.name = name
        self.dependency = dependency
        self.context = context

    def inject(self, instance, value):
        instance.__dict__[self.name] = value 
    
    def extract(self, instance):
        return instance.__dict__[self.name]


class SimpleDependency(BaseDependency):

    def __get__(self, instance: Any, owner: Type):
        if self.name not in instance.__dict__:
            raise AttributeWasNotInjected(f"Attribute {self.name} of class {instance} "
                                          f"was not injected into the object {instance}")
        return self.extract(instance)

    def __set__(self, instance: Any, value: Any):
        self.inject(instance, value)



class LazyDependency(BaseDependency):

    def __get__(self, instance: Any, owner: Type):
        if self.name not in instance.__dict__:
            value = self.context.get_instance(self.dependency.interface)
            self.inject(instance, value)
            return value
        return self.extract(instance)

    def __set__(self, instance: Any, value: Any):
        self.inject(value)



class LazyCollectionDependency(BaseDependency):

    def __get__(self, instance: Any, owner: Type):
        if self.name not in instance.__dict__:
            value = self.context.get_instances(self.dependency.interface)
            value = self.dependency.collection(value)
            self.inject(instance, value)
            return value
        return self.extract(instance)

    def __set__(self, instance: Any, value: Any):
        self.inject(value)


class VolatileDependency(BaseDependency):

    def __get__(self, instance: Any, owner: Type):
        if self.name in instance.__dict__:
            return self.extract(instance)
        return self.context.get_instance(self.dependency.interface)

    def __set__(self, instance: Any, value: Any):
        self.inject(instance, value)


class BaseDependencyBuilder(ABC):

    def __init__(self):
        self.name = None
        self.typehint = None
        self.origin = None

    def is_my_depependency(self, typehint):
        self.origin = get_origin(typehint)
        if self._is_my_dependency(typehint):
            self.typehint = typehint
            return True
        return False

    @abstractmethod
    def _is_my_dependency(self, typehint):
        ...

    @abstractmethod
    def dependency(self, context):
        ...

    @abstractmethod
    def descriptor(self):
        ...


class SimpleDependencyBuilder(BaseDependencyBuilder):

    def _is_my_dependency(self, typehint):
        return self.origin is None

    def dependency(self):
        interface = self.typehint
        return Dependency( interface=interface, 
                           inject_immidiately=True,
                           is_lazy=False,
                           is_volatile=False,
                           collection=None)

    def descriptor(self):
        return SimpleDependency


class CollectionDependencyBuilder(BaseDependencyBuilder):

    def _is_my_dependency(self, typehint):
        return self.origin in (list, set) 

    
    def dependency(self):
        
        interface = get_args(self.typehint)[0]
        return Dependency(interface=interface, 
                          inject_immidiately=True,
                          is_lazy=False,
                          is_volatile=False,
                          collection=self.origin)

    def descriptor(self):
        return SimpleDependency


class LazyDependencyBuilder(BaseDependencyBuilder):
    def __init__(self):
        super().__init__()
        self.child_type = None

    def _is_my_dependency(self, typehint):

        self.child_type = get_args(typehint)[0]
        child_origin = get_origin(self.child_type)  
        return self.origin == Lazy and child_origin not in (list, set)

    def dependency(self):
        interface = self.child_type
        return Dependency(interface=interface,
                          inject_immidiately=False,
                          is_lazy=True,
                          is_volatile=False,
                          collection=None)

    def descriptor(self):
        return LazyDependency


class VolitiledencyBuilder(BaseDependencyBuilder):

    def _is_my_dependency(self, typehint):
        return self.origin == Volatile

    def dependency(self):
        interface = get_args(self.typehint)[0]
        return Dependency(interface=interface, 
                          inject_immidiately=False,
                          is_lazy=False,
                          is_volatile=True,
                          collection=None)

    def descriptor(self):
        return VolatileDependency 


class LazyCollectionDependencyBuilder(BaseDependencyBuilder):

    def _is_my_dependency(self, typehint):
        self.child_type = get_args(typehint)[0]
        child_origin = get_origin(self.child_type)  
        return self.origin == Lazy and child_origin in (list, set)
    
    def dependency(self):
        child_origin = get_origin(self.child_type)  
        interface = get_args(self.child_type)[0] 
        return Dependency(interface=interface, 
                          inject_immidiately=False,
                          is_lazy=True,
                          is_volatile=False,
                          collection=child_origin)

    def descriptor(self):
        return LazyCollectionDependency 


class GroupDependancyBuilder(BaseDependencyBuilder):

    def _is_my_dependency(self, typehint):
        if self.origin != Group:
            return False
        args = get_args(typehint)
        if (len(args) != 2 
            or not isinstance(args[0], ForwardRef)
            or not isinstance(args[0].__forward_arg__, str)
            or not get_origin(args[1]) in (list, set, tuple)):
            raise ImproperlyConfigured(f"Group dependancy arguments must be Group[group_name: str, Collection], {args} given")
        return True

    def dependency(self):
        
        group, collection = get_args(self.typehint)
        group = group.__forward_arg__
        collection = get_origin(collection)
        return Dependency(group=group, 
                          inject_immidiately=True,
                          is_lazy=False,
                          is_volatile=False,
                          collection=collection)

    def descriptor(self):
        return SimpleDependency


def get_dependency_builder(typehint):
    for builder_class in (SimpleDependencyBuilder,
                          GroupDependancyBuilder,                   
                          CollectionDependencyBuilder,
                          LazyDependencyBuilder,
                          VolitiledencyBuilder,
                          LazyCollectionDependencyBuilder):
        builder = builder_class()
        if builder.is_my_depependency(typehint):
            return builder


# TODO lazy[volatile] and volatile[lazy] and volatile[list]


class Builder(Singleton):

    def __init__(self) -> None:
        self._context = None
        self._config = None
        

    def _build_environment(self):
        active_environ = self._config.active_environ
        default_environ = self._config.default_environ
        components = []
        for component in register.components:
            if not component.environ:
                component.environ = {default_environ}
            if ALL in component.environ or active_environ in component.environ:
                components.append(component)
        register.components = components


    def _build_dependencies(self, component: Component):
        cls = component.cls
        if not hasattr(cls, "__annotations__"):
            return
        for name, typehint in component.cls.__annotations__.items():
            dependency_builder = get_dependency_builder(typehint)
            if not dependency_builder:
                continue
            dependency = dependency_builder.dependency()
            descriptor = dependency_builder.descriptor()(dependency=dependency,
                                                       name=name,
                                                       context=self._context)  # TODO remane to get_
            setattr(cls, name, descriptor)
            component.dependencies[name] = (dependency, descriptor)


    def _build_interfaces(self, component: Component):
        for interface in component.implements:
            register.interfaces[interface].append(component)

    def _build_named_components(self, component: Component):
        if not (name := component.name):
            return
        if name in register.named_components:
            raise MoreThanOneCandidateFound(f"More than one named component found, {name}")
        register.named_components[name] = component

    def _build_groups(self, component: Component):
        if not (group := component.group):
            return
        if group not in register.groups:
            register.groups[group] = [component]
            return
        first = register.groups[group][0]
        if first is component:
            return
        if set(first.dependencies) != set(component.dependencies):
            raise InconsistentGroup(f"Components in group {group} differ in their dependencies")
        if first.scope != component.scope:
            raise InconsistentGroup(f"Components in group {group} differ in their scope")
        if set(first.implements) != set(component.implements):
            raise InconsistentGroup(f"Components in group {group} differ in their interfaces")
        register.groups.setdefault(group, []).append(component)
    
    def _build_factories(self, component: Component):
        if component.factory_name:
            if register.get_factory(component.factory_name) is None:
                raise ImproperlyConfigured(f"Factory '{component.factory_name}'"
                 f"required for component {component} does not exist")

    def _build_scopes(self, component: Component):
        if component.scope not in register.scopes:
            raise ScopeNotFound(f"Scope {component.scope} for component {component.cls} not registered")

    def build(self):
        self._build_environment()
        for component in register.components:
            self._build_interfaces(component)
            self._build_dependencies(component)
            self._build_named_components(component)
            self._build_groups(component)
            self._build_scopes(component)
            self._build_factories(component)


builder = Builder()
