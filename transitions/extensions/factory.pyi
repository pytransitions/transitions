from ..core import Machine, State
from .diagrams import GraphMachine, NestedGraphTransition, HierarchicalGraphMachine
from .locking import LockedMachine
from .nesting import HierarchicalMachine, NestedEvent
from typing import Type, Dict, Tuple, Callable, Union

try:
    from transitions.extensions.asyncio import AsyncMachine, AsyncTransition
    from transitions.extensions.asyncio import HierarchicalAsyncMachine, NestedAsyncTransition
except (ImportError, SyntaxError):
    # Mocks for Python version 3.6 and earlier
    class AsyncMachine:  # type: ignore
        pass

    class AsyncTransition:  # type: ignore
        pass

    class HierarchicalAsyncMachine:  # type: ignore
        pass

    class NestedAsyncTransition:  # type: ignore
        pass


class MachineFactory:
    @staticmethod
    def get_predefined(graph: bool = ..., nested: bool = ...,
                       locked: bool = ..., asyncio: bool = ...) -> Union[
        Type[Machine], Type[HierarchicalMachine], Type[AsyncMachine], Type[HierarchicalAsyncMachine],
        Type[GraphMachine], Type[HierarchicalGraphMachine], Type[AsyncGraphMachine],
        Type[HierarchicalAsyncGraphMachine], Type[LockedMachine], Type[LockedHierarchicalMachine],
        Type[LockedGraphMachine], Type[LockedHierarchicalGraphMachine]
    ]: ...

class LockedHierarchicalMachine(LockedMachine, HierarchicalMachine):  # type: ignore[misc]
    # replaces LockedEvent with NestedEvent; method overridden by LockedEvent is not used in HSMs
    event_cls: Type[NestedEvent]  # type: ignore
    def _get_qualified_state_name(self, state: State) -> str: ...

class LockedGraphMachine(GraphMachine, LockedMachine):  # type: ignore
    @staticmethod
    def format_references(func: Callable) -> str: ...

class LockedHierarchicalGraphMachine(GraphMachine, LockedHierarchicalMachine):  # type: ignore
    transition_cls: Type[NestedGraphTransition]
    event_cls: Type[NestedEvent]
    @staticmethod
    def format_references(func: Callable) -> str: ...

class AsyncGraphMachine(GraphMachine, AsyncMachine):
    # AsyncTransition already considers graph models when necessary
    transition_cls: Type[AsyncTransition]  # type: ignore

class HierarchicalAsyncGraphMachine(GraphMachine, HierarchicalAsyncMachine):  # type: ignore
    # AsyncTransition already considers graph models when necessary
    transition_cls: Type[NestedAsyncTransition]  # type: ignore

_CLASS_MAP: Dict[Tuple[bool, bool, bool, bool], Type[Machine]]
