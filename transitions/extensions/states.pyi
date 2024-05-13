from ..core import State, EventData, Callback, CallbacksArg

from enum import Enum
from logging import Logger
from threading import Timer
from typing import List, Union, Any, Dict, Optional, Type

_LOGGER: Logger

class Tags(State):
    tags: Logger
    def __init__(self, name: Union[str, Enum], on_enter: CallbacksArg = ..., on_exit: CallbacksArg = ...,
                 ignore_invalid_triggers: bool = ..., final: bool = ..., tags: Union[List[str], str, None] = ...) -> None : ...
class Error(Tags):
    pass

class Timeout(State):
    dynamic_methods: List[str]
    timeout: float
    _on_timeout: Optional[List[Callback]]
    runner: Dict[int, Timer]
    def __init__(self, *args: List[Any], **kwargs: Dict[str, Any]) -> None: ...
    def enter(self, event_data: EventData) -> None: ...
    def exit(self, event_data: EventData) -> None: ...
    def _process_timeout(self, event_data: EventData) -> None: ...
    @property
    def on_timeout(self) -> List[Callback]: ...
    @on_timeout.setter
    def on_timeout(self, value: Union[Callback, List[Callback]]) -> None: ...

class Volatile(State):
    volatile_cls: Any
    volatile_hook: str
    initialized: bool
    def __init__(self, *args: List[Any], **kwargs: Dict[str, Any]) -> None: ...
    def enter(self, event_data: EventData) -> None: ...
    def exit(self, event_data: EventData) -> None: ...

def add_state_features(*args: Union[Type[State], List[Type[State]]]) -> Any: ...

class VolatileObject: ...
