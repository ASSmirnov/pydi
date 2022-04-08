from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, _ProtocolMeta, Type, List, Dict, Optional, Set, TypeVar, Generic, Tuple
from .exceptions import FinishedSingletonUsage

ALL = "all"


@dataclass
class Dependency:
    interface: Type = None
    collection: Type = None
    group: Optional[str] = None
    is_lazy: bool = False
    is_volatile: bool = False
    inject_immidiately: bool = False
    use_strategy: bool = False


@dataclass
class Component:
    cls: Type
    scope: str
    uid: int
    implements: List[Type] = field(default_factory=list)
    environ: Set[str] = field(default_factory=list)
    name: Optional[str] = None
    group: Optional[str] = None # TODO list of groups
    dependencies: Dict[str, Tuple[Dependency, Any]] = field(default_factory=dict) #TODO descriptor protocol
    factory_name: Optional[str] = None


class Singleton:
    __readonly__ = False

    _instance = None
    _finished = False

    def __new__(cls, *args, **kwargs):
        if cls._finished:
            raise FinishedSingletonUsage(f"Singleton {cls.__name__} was finished")
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __getattribute__(self, item: str):
        if item in ("__class__", "_finished", "__readonly__"):
            return super().__getattribute__(item)
        if self._finished and not self.__readonly__:
            raise FinishedSingletonUsage(f"Singleton {self.__class__.__name__} was finished")
        return super().__getattribute__(item)

    def __setattr__(self, name: str, value: Any) -> None:
        if  self._finished:
           raise FinishedSingletonUsage(f"Singleton {self.__class__.__name__} was finished")
        return super().__setattr__(name, value) 

    @classmethod
    def finalize(cls):
        cls._instance = None
        cls._finished = True


class Scope(ABC):
    @abstractmethod
    def enter(self):
        pass

    @abstractmethod
    def exit(self):
        pass

    @abstractmethod
    def get_instance(self, component: Component, **kwargs):
        pass


T = TypeVar('T', bound=_ProtocolMeta)


class Lazy(Generic[T]):
    pass


class Volatile(Generic[T]):
    pass


Col = TypeVar("Col", List, Set, Tuple)


class Group(Generic[T, Col]):
    pass


class Strategy(Generic[T]):
    pass
