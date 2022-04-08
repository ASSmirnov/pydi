class IllegalContextCall(Exception):
    pass


class ImproperlyConfigured(Exception):
    pass


class AlreadyStarted(Exception):
    pass


class NotStarted(Exception):
    pass


class ScopeIsNotActive(Exception):
    pass


class GroupNotFound(ImproperlyConfigured):
    pass


class GroupFactoryNotFound(ImproperlyConfigured):
    pass


class InconsistentGroup(ImproperlyConfigured):
    pass


class ScopeNotFound(ImproperlyConfigured):
    pass


class ScopeRedeclaration(ImproperlyConfigured):
    pass


class WrongInstantiating(Exception):
    pass


class NoCandidatesFound(WrongInstantiating):
    pass


class MoreThanOneCandidateFound(WrongInstantiating):
    pass


class FinishedSingletonUsage(Exception):
    pass


class SingletonError(WrongInstantiating):
    pass


class AttributeWasNotInjected(Exception):
    pass
