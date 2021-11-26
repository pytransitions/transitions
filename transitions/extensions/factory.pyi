from ..core import Machine, State
from .diagrams import GraphMachine, NestedGraphTransition
from .locking import LockedMachine
from .nesting import HierarchicalMachine, NestedEvent
from typing import Type, Dict, Tuple, Callable, Union

try:
    from transitions.extensions.asyncio import AsyncMachine, AsyncTransition
    from transitions.extensions.asyncio import HierarchicalAsyncMachine, NestedAsyncTransition
except (ImportError, SyntaxError):
    class AsyncMachine:  # Mocks for Python version 3.6 and earlier
        pass

    class AsyncTransition:
        pass

    class HierarchicalAsyncMachine:
        pass

    class NestedAsyncTransition:
        pass


class MachineFactory:
    @staticmethod
    def get_predefined(graph: bool = ..., nested: bool = ...,
                       locked: bool = ..., asyncio: bool = ...) -> Union[Type[Machine], Type[HierarchicalMachine]]: ...

class LockedHierarchicalMachine(LockedMachine, HierarchicalMachine):
    event_cls: NestedEvent
    def _get_qualified_state_name(self, state: State) -> str: ...

class LockedGraphMachine(GraphMachine, LockedMachine):
    @staticmethod
    def format_references(func): ...

class LockedHierarchicalGraphMachine(GraphMachine, LockedHierarchicalMachine):
    transition_cls: NestedGraphTransition
    event_cls: NestedEvent
    @staticmethod
    def format_references(func: Callable) -> str: ...

class AsyncGraphMachine(GraphMachine, AsyncMachine):
    transition_cls: AsyncTransition

class HierarchicalAsyncGraphMachine(GraphMachine, HierarchicalAsyncMachine):
    transition_cls: NestedAsyncTransition

_CLASS_MAP: Dict[Tuple[bool, bool, bool, bool], Type[Machine]]
