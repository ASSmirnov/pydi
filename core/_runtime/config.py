from typing import Set

from ..base import Singleton


class Config(Singleton):

    __readonly__ = True
    
    def __init__(self):
        self.active_environ: str = None
        self.default_environ: Set[str] = None


config = Config()
