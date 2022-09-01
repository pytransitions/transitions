from ..core import Condition, Event, EventData, Machine, State, Transition, StateConfig, ModelParameter, TransitionConfig
from .nesting import HierarchicalMachine, NestedEvent, NestedState, NestedTransition
from typing import Any, Optional, List, Type, Dict, Deque, Callable, Union, Iterable, DefaultDict, Literal, Sequence
from asyncio import Task
from functools import partial
from logging import Logger
from enum import Enum
from contextvars import ContextVar

from ..core import StateIdentifier, CallbacksArg, CallbackList

_LOGGER: Logger

class AsyncState(State):
    async def enter(self, event_data: AsyncEventData) -> None: ...  # type: ignore[override]
    async def exit(self, event_data: AsyncEventData) -> None: ...  # type: ignore[override]

class NestedAsyncState(NestedState, AsyncState):
    _scope: Any
    async def scoped_enter(self, event_data: AsyncEventData, scope: Optional[List[str]] = ...) -> None: ...  # type: ignore[override]
    async def scoped_exit(self, event_data: AsyncEventData, scope: Optional[List[str]] = ...) -> None: ...  # type: ignore[override]

class AsyncCondition(Condition):
    async def check(self, event_data: AsyncEventData) -> bool: ...  # type: ignore[override]

class AsyncTransition(Transition):
    condition_cls: Type[AsyncCondition]
    async def _eval_conditions(self, event_data: AsyncEventData) -> bool: ...  # type: ignore[override]
    async def execute(self, event_data: AsyncEventData) -> bool: ...  # type: ignore[override]
    async def _change_state(self, event_data: AsyncEventData) -> None: ...  # type: ignore[override]

class NestedAsyncTransition(AsyncTransition, NestedTransition):
    async def _change_state(self, event_data: AsyncEventData) -> None: ...  # type: ignore[override]

class AsyncEventData(EventData):
    machine: Union[AsyncMachine, HierarchicalAsyncMachine]
    transition: AsyncTransition
    source_name: Optional[str]
    source_path: Optional[List[str]]

class AsyncEvent(Event):
    machine: AsyncMachine
    transitions: DefaultDict[str, List[AsyncTransition]]  # type: ignore

    async def trigger(self, model: object, *args: List, **kwargs: Dict[str, Any]) -> bool: ...  # type: ignore[override]
    async def _trigger(self, event_data: AsyncEventData) -> bool: ...  # type: ignore[override]
    async def _process(self, event_data: AsyncEventData) -> bool: ...  # type: ignore[override]

class NestedAsyncEvent(NestedEvent):
    transitions: DefaultDict[str, List[NestedAsyncTransition]]  # type: ignore

    async def trigger_nested(self, event_data: AsyncEventData) -> bool: ...  # type: ignore[override]
    async def _process(self, event_data: AsyncEventData) -> bool: ...  # type: ignore[override]

class AsyncMachine(Machine):
    state_cls: Type[NestedAsyncState]
    transition_cls: Type[AsyncTransition]
    event_cls: Type[AsyncEvent]
    async_tasks: Dict[int, List[Task]]
    events: Dict[str, AsyncEvent]  # type: ignore
    queued: Union[bool, Literal["model"]]
    protected_tasks: List[Task]
    current_context: ContextVar
    _transition_queue_dict: Dict[int, Deque[Callable]]
    def __init__(self, model: Optional[ModelParameter] = ...,
                 states: Optional[Union[Sequence[StateConfig], Type[Enum]]] = ...,
                 initial: Optional[StateIdentifier] = ...,
                 transitions: Optional[Union[TransitionConfig, Sequence[TransitionConfig]]] = ...,
                 send_event: bool = ..., auto_transitions: bool = ..., ordered_transitions: bool = ...,
                 ignore_invalid_triggers: Optional[bool] = ...,
                 before_state_change: CallbacksArg = ..., after_state_change: CallbacksArg = ...,
                 name: str = ..., queued: Union[bool, Literal["model"]] = ...,
                 prepare_event: CallbacksArg = ..., finalize_event: CallbacksArg = ...,
                 model_attribute: str = ..., on_exception: CallbacksArg = ..., **kwargs: Dict[str, Any]) -> None: ...
    def add_model(self, model: Union[Union[Literal["self"], object], Sequence[Union[Literal["self"], object]]],
                  initial: Optional[StateIdentifier] = ...) -> None: ...
    async def dispatch(self, trigger: str, *args: List, **kwargs: Dict[str, Any]) -> bool: ...  # type: ignore[override]
    async def callbacks(self, funcs: Iterable[Union[str, Callable]], event_data: AsyncEventData) -> None: ...  # type: ignore[override]
    async def callback(self, func: Union[str, Callable], event_data: AsyncEventData) -> None: ...  # type: ignore[override]
    @staticmethod
    async def await_all(callables: List[Callable]) -> List: ...
    async def switch_model_context(self, model: object) -> None: ...
    def get_state(self, state: Union[str, Enum]) -> AsyncState: ...
    async def process_context(self, func: partial, model: object) -> bool: ...
    def remove_model(self, model: object) -> None: ...
    def _process(self, trigger: partial) -> bool: ...
    async def _process_async(self, trigger: partial, model: object) -> bool: ...


class HierarchicalAsyncMachine(HierarchicalMachine, AsyncMachine):  # type: ignore
    state_cls: Type[NestedAsyncState]
    transition_cls: Type[NestedAsyncTransition]
    event_cls: Type[NestedAsyncEvent]  # type: ignore
    async def trigger_event(self, model: object, trigger: str, # type: ignore[override]
                            *args: List, **kwargs: Dict[str, Any]) -> bool: ...
    async def _trigger_event(self, event_data: AsyncEventData, trigger: str) -> bool: ...  # type: ignore[override]


class AsyncTimeout(AsyncState):
    dynamic_methods: List[str]
    timeout: float
    _on_timeout: CallbacksArg
    runner: Dict[int, Task]
    def __init__(self, *args: List, **kwargs: Dict[str, Any]) -> None: ...
    async def enter(self, event_data: AsyncEventData) -> None: ...  # type: ignore[override]
    async def exit(self, event_data: AsyncEventData) -> None: ...  # type: ignore[override]
    def create_timer(self, event_data: AsyncEventData) -> Task: ...
    async def _process_timeout(self, event_data: AsyncEventData) -> None: ...
    @property
    def on_timeout(self) -> CallbackList: ...
    @on_timeout.setter
    def on_timeout(self, value: CallbacksArg) -> None: ...

class _DictionaryMock(dict):
    _value: Any
    def __init__(self, item: Any) -> None: ...
    def __setitem__(self, key: Any, item: Any) -> None: ...
    def __getitem__(self, key: Any) -> Any: ...
    def __repr__(self) -> str: ...
