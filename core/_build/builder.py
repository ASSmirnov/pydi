from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ForwardRef, Optional, get_origin, get_args, Any, Type

from ..base import Group, Lazy, Singleton, Component, Dependency, ALL, Volatile, Strategy
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

@dataclass
class ParsingResult:
    interface: Optional[Type] = None
    collection: Optional[Type] = None 
    is_lazy: bool = False
    is_volatile: bool = False
    group_name: Optional[str] = None
    use_strategy: bool = False



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
        if not register.is_interface(interface) or VarType:
            return False
        return Dependency( interface=interface, 
                           inject_immidiately=True)

    def descriptor(self):
        return SimpleDependency


class CollectionDependencyBuilder(BaseDependencyBuilder):

    def _is_my_dependency(self, typehint):
        return self.origin in (list, set) 

    
    def dependency(self):
        
        interface = get_args(self.typehint)[0]
        return Dependency(interface=interface, 
                          inject_immidiately=True,
                          collection=self.origin)

    def descriptor(self):
        return SimpleDependency


class LazyDependencyBuilder(BaseDependencyBuilder):
    def __init__(self):
        super().__init__()
        self.child_type = None

    def _is_my_dependency(self, typehint):
        if self.origin != Lazy:
            return False
        self.child_type = get_args(typehint)[0]
        child_origin = get_origin(self.child_type)  
        if child_origin == Volatile:
            raise ImproperlyConfigured("Lazy[Volatile] dependencies make no sense and not supported")
        return child_origin not in (list, set, tuple)

    def dependency(self):
        interface = self.child_type
        return Dependency(interface=interface,
                          is_lazy=True)

    def descriptor(self):
        return LazyDependency


class VolitiledencyBuilder(BaseDependencyBuilder):

    def _is_my_dependency(self, typehint):
        if self.origin != Volatile:
            return False
        self.child_type = get_args(typehint)[0]
        child_origin = get_origin(self.child_type)  
        if child_origin == Lazy:
            raise ImproperlyConfigured("Volatile[Lazy]] dependencies make no sense and are not supported")
        if child_origin in (list, set, tuple):
            raise ImproperlyConfigured(f"Volatile[{child_origin}]] dependencies are not supported")

        return False


    def dependency(self):
        interface = get_args(self.typehint)[0]
        return Dependency(interface=interface, 
                          is_volatile=True)

    def descriptor(self):
        return VolatileDependency 


class LazyCollectionDependencyBuilder(BaseDependencyBuilder):

    def _is_my_dependency(self, typehint):
        self.child_type = get_args(typehint)[0]
        child_origin = get_origin(self.child_type)  
        return self.origin == Lazy and child_origin in (list, set, tuple)
    
    def dependency(self):
        child_origin = get_origin(self.child_type)  
        interface = get_args(self.child_type)[0] 
        return Dependency(interface=interface, 
                          is_lazy=True,
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
                          collection=collection)

    def descriptor(self):
        return SimpleDependency


class StrategyDependencyBuilder(BaseDependencyBuilder):

    def _is_my_dependency(self, typehint):
        if self.origin != Strategy:
            return False 
        args = get_args(typehint)
        if len(args) != 1:
            raise ImproperlyConfigured(f"Strategy[group_name: str] expected, {args} given")
        child_origin = get_origin(args[0])  
        if (child_origin in (list, set, tuple)
            or not isinstance(child_origin, ForwardRef) 
            or not isinstance(child_origin .__forward_arg__, str)):
            raise ImproperlyConfigured(f"Strategy[{child_origin}] makes no sense and is not supported")
        return True 
    
    def dependency(self):
        group = get_args(self.typehint)
        group = group.__forward_arg__
        collection = get_origin(collection)
        return Dependency(group=group, 
                          inject_immidiately=True,
                          use_strategy=True)

    def descriptor(self):
        return SimpleDependency

def _parse_type_hint(typehint, result=None):
    origin = get_origin(typehint)
    result = result or ParsingResult()
    if origin in (list, set, tuple):
        result.collection = origin
    elif register.is_interface(origin):
        result.interface = origin
    else:
        return
    children = get_args(typehint)
    if len(children) > 1:
        raise ImproperlyConfigured(f"One of Interface, Interface[Lazy], Interface[Volatile], "
                                   f"List[Interface[Group["name"]]], List[Interface], Interface[Strategy["name"]] expected,
                                   f"but {typehint} given")
    nested = children[0]
    nested_origin = get_origin(nested)
    if nested_origin == Lazy:
        result.is_lazy = True
    elif nested_origin == Volatile:
        result.is_volatile = True
    elif register.is_interface(nested_origin):
        return _parse_type_hint(nested, result=result)
    elif nested_origin == Group:
        result.group_name = get_args(nested)[0].__forward_arg__ 
    elif nested_origin == Strategy:
        result.group_name = get_args(nested)[0].__forward_arg__ 
        result.use_strategy = True
    else:
        raise ImproperlyConfigured(f"One of Interface, Interface[Lazy], Interface[Volatile], "
                                   f"List[Interface[Group["name"]]], List[Interface], Interface[Strategy["name"]] expected,
                                   f"but {typehint} given")
    return result


def _validate_type_hint(parsing_result):
    pass 

def get_dependency_builder(typehint):
    parsing_result = _parse_type_hint(typehint)
    if not parsing_result:
        return
    

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
