from contextlib import AbstractContextManager
from transitions.core import Event, Machine, ModelParameter, TransitionConfig, CallbacksArg, StateConfig
from typing import Any, Dict, Literal, Optional, Type, List, DefaultDict, Union, Callable, Sequence
from types import TracebackType
from logging import Logger
from threading import Lock
from enum import Enum

from ..core import StateIdentifier, State

_LOGGER: Logger

LockContext = AbstractContextManager[None]

class PicklableLock(LockContext):
    lock: Lock
    def __init__(self) -> None: ...
    def __getstate__(self) -> Dict[str, Any]: ...
    def __setstate__(self, value: Dict[str, Any]) -> PicklableLock: ...
    def __enter__(self) -> None: ...
    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException],
                 exc_tb: Optional[TracebackType]) -> None: ...

class IdentManager(LockContext):
    current: int
    def __init__(self) -> None: ...
    def __enter__(self) -> None: ...
    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException],
                 exc_tb: Optional[TracebackType]) -> None: ...

class LockedEvent(Event):
    machine: LockedMachine
    def trigger(self, model: object, *args: List[Any], **kwargs: Dict[str, Any]) -> bool: ...


class LockedMachine(Machine):
    event_cls: Type[LockedEvent]
    _ident: IdentManager
    machine_context: List[LockContext]
    model_context_map: DefaultDict[int, List[LockContext]]
    def __init__(self, model: Optional[ModelParameter] = ...,
                 states: Optional[Union[Sequence[StateConfig], Type[Enum]]] = ...,
                 initial: Optional[StateIdentifier] = ...,
                 transitions: Optional[Union[TransitionConfig, Sequence[TransitionConfig]]] = ...,
                 send_event: bool = ..., auto_transitions: bool = ..., ordered_transitions: bool = ...,
                 ignore_invalid_triggers: Optional[bool] = ...,
                 before_state_change: CallbacksArg = ..., after_state_change: CallbacksArg = ...,
                 name: str = ..., queued: bool = ...,
                 prepare_event: CallbacksArg = ..., finalize_event: CallbacksArg = ...,
                 model_attribute: str = ..., on_exception: CallbacksArg = ...,
                 machine_context: Optional[Union[List[LockContext], LockContext]] = ...,
                 **kwargs: Dict[str, Any]) -> None: ...
    def __getstate__(self) -> Dict[str, Any]: ...
    def __setstate__(self, state: Dict[str, Any]) -> None: ...
    def add_model(self, model:  Union[Union[Literal['self'], object], List[Union[Literal['self'], object]]],
                  initial: Optional[StateIdentifier] = ...,
                  model_context: Optional[Union[LockContext, List[LockContext]]] = ...) -> None: ...
    def remove_model(self, model: Union[Union[Literal['self'], object],
                                        List[Union[Literal['self'], object]]]) -> None: ...
    def __getattribute__(self, item: str) -> Any: ...
    def __getattr__(self, item: str) -> Any: ...
    def _add_model_to_state(self, state: State, model: object) -> None: ...
    def _get_qualified_state_name(self, state: State) -> str: ...
    def _locked_method(self, func: Callable[..., Any], *args: List[Any], **kwargs: Dict[str, Any]) -> Any: ...
