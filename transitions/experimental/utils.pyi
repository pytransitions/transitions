from typing import Union, Callable, List, Optional, Iterable, Type, ClassVar, Tuple, Dict, Any, DefaultDict, Deque
from transitions.core import StateIdentifier, CallbacksArg, CallbackFunc, Machine, TransitionConfig, MachineConfig
from transitions.extensions.markup import MarkupConfig

_placeholder_body: str

def generate_base_model(config: Union[MachineConfig, MarkupConfig]) -> str: ...

def with_model_definitions(cls: Type[Machine]) -> Type[Machine]: ...

def add_transitions(*configs: TransitionConfig) -> Callable[[CallbackFunc], CallbackFunc]: ...
def event(*configs: TransitionConfig) -> Callable[..., Optional[bool]]: ...

def transition(source: Union[StateIdentifier, List[StateIdentifier]],
                dest: Optional[StateIdentifier] = ...,
                conditions: CallbacksArg = ..., unless: CallbacksArg = ...,
                before: CallbacksArg = ..., after: CallbacksArg = ...,
                prepare: CallbacksArg = ...) -> TransitionConfig: ...

class TriggerPlaceholder:
    definitions: ClassVar[DefaultDict[type, DefaultDict[str, List[TransitionConfig]]]]
    configs: Deque[TransitionConfig]
    def __init__(self, configs: Iterable[TransitionConfig]) -> None: ...

    def __set_name__(self, owner: type, name: str) -> None: ...

    def __call__(self, *args: Tuple[Any], **kwargs: Dict[str, Any]) -> Optional[bool]: ...
