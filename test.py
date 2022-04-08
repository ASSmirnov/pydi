from typing import Protocol, List
from core.decorators import component, interface
from abdi import context, configure
from core.base import Lazy, Volatile

@interface
class ITest(Protocol):

    def test(self):
        ...


@interface
class ISimpleService(Protocol):

    def do(self):
        ...


@component(implements=ISimpleService, scope="singleton")
class SimpleService:

    def do(self):
        print("Test instance")


@component(implements=ITest, scope="singleton")
class Test:

    simple_service: ISimpleService
    simple_service_list: List[ISimpleService]

    def test(self):
        print("Test instance")


@component(implements=ITest, scope="singleton", name="Super")
class Test2:

    simple_service: ISimpleService
    simple_service_list: List[ISimpleService]
    lazy: Lazy[ISimpleService]

    def test(self):
        print("Test instance")

configure()
print(context.get_component(name="Super"))

