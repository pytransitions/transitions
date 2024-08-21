from ..core import Callback, Condition, Event, EventData, Machine, State, Transition, StateConfig, ModelParameter, \
    TransitionConfigList
from .nesting import HierarchicalMachine, NestedEvent, NestedState, NestedTransition, NestedEventData, \
    NestedStateConfig, NestedStateIdentifier
from typing import Any, Awaitable, Optional, List, Type, Dict, Deque, Callable, Union, Iterable, DefaultDict, Literal, \
    Sequence, Coroutine, Required, TypedDict, Collection
from asyncio import Task
from logging import Logger
from enum import Enum
from contextvars import ContextVar

from ..core import StateIdentifier, CallbackList

_LOGGER: Logger

AsyncCallbackFunc = Callable[..., Coroutine[Any, Any, Optional[bool]]]
AsyncCallback = Union[str, AsyncCallbackFunc]
AsyncCallbacksArg = Optional[Union[Callback, Iterable[Callback], AsyncCallback, Iterable[AsyncCallback]]]

class AsyncTransitionConfigDict(TypedDict, total=False):
    trigger: Required[str]
    source: Required[Union[str, Enum, Sequence[Union[str, Enum]]]]
    dest: Required[Optional[Union[str, Enum]]]
    prepare: AsyncCallbacksArg
    before: AsyncCallbacksArg
    after: AsyncCallbacksArg
    conditions: AsyncCallbacksArg
    unless: AsyncCallbacksArg

# For backwards compatibility we also accept generic collections
AsyncTransitionConfig = Union[TransitionConfigList, AsyncTransitionConfigDict, Collection[str]]

class AsyncState(State):
    async def enter(self, event_data: AsyncEventData) -> None: ...  # type: ignore[override]
    async def exit(self, event_data: AsyncEventData) -> None: ...  # type: ignore[override]
    def add_callback(self, trigger: str, func: AsyncCallback) -> Awaitable[Optional[bool]]: ...  # type: ignore[override]

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
    machine: AsyncMachine
    transition: AsyncTransition
    source_name: Optional[str]
    source_path: Optional[List[str]]

class NestedAsyncEventData(NestedEventData, AsyncEventData):
    machine: HierarchicalAsyncMachine
    transition: NestedAsyncTransition

class AsyncEvent(Event):
    machine: AsyncMachine
    transitions: DefaultDict[str, List[AsyncTransition]]  # type: ignore

    async def trigger(self, model: object, *args: Any, **kwargs: Any) -> bool: ...  # type: ignore[override]
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
    async_tasks: Dict[int, List[Task[Any]]]
    events: Dict[str, AsyncEvent]  # type: ignore
    queued: Union[bool, Literal["model"]]
    protected_tasks: List[Task[Any]]
    current_context: ContextVar[Optional[Task[Any]]]
    _transition_queue_dict: Dict[int, Deque[AsyncCallbackFunc]]
    _queued = Union[bool, str]
    def __init__(self, model: Optional[ModelParameter] = ...,
                 states: Optional[Union[Sequence[StateConfig], Type[Enum]]] = ...,
                 initial: Optional[StateIdentifier] = ...,
                 transitions: Optional[Sequence[AsyncTransitionConfig]] = ...,
                 send_event: bool = ..., auto_transitions: bool = ..., ordered_transitions: bool = ...,
                 ignore_invalid_triggers: Optional[bool] = ...,
                 before_state_change: AsyncCallbacksArg = ..., after_state_change: AsyncCallbacksArg = ...,
                 name: str = ..., queued: Union[bool, Literal["model"]] = ...,
                 prepare_event: AsyncCallbacksArg = ..., finalize_event: AsyncCallbacksArg = ...,
                 model_attribute: str = ..., model_override: bool= ..., on_exception: AsyncCallbacksArg = ...,
                 on_final: AsyncCallbacksArg = ..., **kwargs: Any) -> None: ...
    def add_model(self, model: Union[Union[Literal["self"], object], Sequence[Union[Literal["self"], object]]],
                  initial: Optional[StateIdentifier] = ...) -> None: ...
    def add_transition(self, trigger: str,
                       source: Union[StateIdentifier, List[StateIdentifier]],
                       dest: Optional[StateIdentifier] = ...,
                       conditions: AsyncCallbacksArg = ..., unless: AsyncCallbacksArg = ...,
                       before: AsyncCallbacksArg = ..., after: AsyncCallbacksArg = ..., prepare: AsyncCallbacksArg = ...,
                       **kwargs: Any) -> None: ...
    def add_transitions(self, transitions: Sequence[AsyncTransitionConfig] = ...) -> None: ...
    async def dispatch(self, trigger: str, *args: Any, **kwargs: Any) -> bool: ...  # type: ignore[override]
    async def callbacks(self, funcs: Iterable[Callback], event_data: AsyncEventData) -> None: ...  # type: ignore[override]
    async def callback(self, func: AsyncCallback, event_data: AsyncEventData) -> None: ...  # type: ignore[override]
    @staticmethod
    async def await_all(callables: List[AsyncCallbackFunc]) -> List[Optional[bool]]: ...
    async def cancel_running_transitions(self, model: object, msg: Optional[str] = ...) -> None: ...
    async def switch_model_context(self, model: object) -> None: ...
    def get_state(self, state: Union[str, Enum]) -> AsyncState: ...
    async def process_context(self, func: Callable[[], Awaitable[None]], model: object) -> bool: ...
    def remove_model(self, model: object) -> None: ...
    async def _process_async(self, trigger: Callable[[], Awaitable[None]], model: object) -> bool: ...


class HierarchicalAsyncMachine(HierarchicalMachine, AsyncMachine):  # type: ignore
    state_cls: Type[NestedAsyncState]
    transition_cls: Type[NestedAsyncTransition]
    event_cls: Type[NestedAsyncEvent]  # type: ignore
    def __init__(self, model: Optional[ModelParameter]=...,
                 states: Optional[Union[Sequence[NestedStateConfig], Type[Enum]]] = ...,
                 initial: Optional[NestedStateIdentifier] = ...,
                 transitions: Sequence[AsyncTransitionConfig] = ...,
                 send_event: bool = ..., auto_transitions: bool = ..., ordered_transitions: bool = ...,
                 ignore_invalid_triggers: Optional[bool] = ...,
                 before_state_change: AsyncCallbacksArg = ..., after_state_change: AsyncCallbacksArg = ...,
                 name: str = ..., queued: Union[bool, str] = ...,
                 prepare_event: AsyncCallbacksArg = ..., finalize_event: AsyncCallbacksArg = ...,
                 model_attribute: str = ..., on_exception: AsyncCallbacksArg = ..., **kwargs: Any) -> None: ...
    async def trigger_event(self, model: object, trigger: str,  # type: ignore[override]
                            *args: Any, **kwargs: Any) -> bool: ...
    async def _trigger_event(self, event_data: NestedAsyncEventData, trigger: str) -> bool: ...  # type: ignore[override]

    def get_state(self, state: Union[str, Enum, List[str]], hint: Optional[List[str]] = ...) -> NestedAsyncState: ...


class AsyncTimeout(AsyncState):
    dynamic_methods: List[str]
    timeout: float
    _on_timeout: AsyncCallbacksArg
    runner: Dict[int, Task[Any]]
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    async def enter(self, event_data: AsyncEventData) -> None: ...  # type: ignore[override]
    async def exit(self, event_data: AsyncEventData) -> None: ...  # type: ignore[override]
    def create_timer(self, event_data: AsyncEventData) -> Task[Any]: ...
    async def _process_timeout(self, event_data: AsyncEventData) -> None: ...
    @property
    def on_timeout(self) -> CallbackList: ...
    @on_timeout.setter
    def on_timeout(self, value: AsyncCallbacksArg) -> None: ...

class _DictionaryMock(Dict[Any, Any]):
    _value: Any
    def __init__(self, item: Any) -> None: ...
    def __setitem__(self, key: Any, item: Any) -> None: ...
    def __getitem__(self, key: Any) -> Any: ...
    def __repr__(self) -> str: ...
