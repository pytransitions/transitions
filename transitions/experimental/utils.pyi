from typing import Union, Callable, List, Optional, Iterable, Type, ClassVar, Any, DefaultDict, Deque, \
    Sequence, TypedDict, Required

from enum import Enum
from transitions.core import StateIdentifier, CallbacksArg, CallbackFunc, Machine, MachineConfig, \
    TransitionConfigList
from transitions.extensions.asyncio import AsyncCallbacksArg
from transitions.extensions.markup import MarkupConfig

_placeholder_body: str

class TransitionConfigDictWithoutTrigger(TypedDict, total=False):
    source: Required[Union[str, Enum, Sequence[Union[str, Enum]]]]
    dest: Required[Optional[Union[str, Enum]]]
    prepare: Union[CallbacksArg, AsyncCallbacksArg]
    before: Union[CallbacksArg, AsyncCallbacksArg]
    after: Union[CallbacksArg, AsyncCallbacksArg]
    conditions: Union[CallbacksArg, AsyncCallbacksArg]
    unless: Union[CallbacksArg, AsyncCallbacksArg]

TransitionConfigWithoutTrigger =  Union[TransitionConfigList, TransitionConfigDictWithoutTrigger]

def generate_base_model(config: Union[MachineConfig, MarkupConfig]) -> str: ...

def with_model_definitions(cls: Type[Machine]) -> Type[Machine]: ...

def add_transitions(*configs: TransitionConfigWithoutTrigger) -> Callable[[CallbackFunc], CallbackFunc]: ...
def event(*configs: TransitionConfigWithoutTrigger) -> Callable[..., Optional[bool]]: ...

def transition(source: Union[StateIdentifier, List[StateIdentifier]],
                dest: Optional[StateIdentifier] = ...,
                conditions: CallbacksArg = ..., unless: CallbacksArg = ...,
                before: CallbacksArg = ..., after: CallbacksArg = ...,
                prepare: CallbacksArg = ...) -> TransitionConfigWithoutTrigger: ...

class TriggerPlaceholder:
    definitions: ClassVar[DefaultDict[type, DefaultDict[str, List[TransitionConfigWithoutTrigger]]]]
    configs: Deque[TransitionConfigWithoutTrigger]
    def __init__(self, configs: Iterable[TransitionConfigWithoutTrigger]) -> None: ...

    def __set_name__(self, owner: type, name: str) -> None: ...

    def __call__(self, *args: Any, **kwargs: Any) -> Optional[bool]: ...
