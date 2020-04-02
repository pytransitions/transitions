"""
    transitions.extensions.factory
    ------------------------------

    This module contains the definitions of classes which combine the functionality of transitions'
    extension modules. These classes can be accessed by names as well as through a static convenience
    factory object.
"""

from ..core import Machine

from .nesting import HierarchicalMachine, NestedTransition, NestedEvent
from .locking import LockedMachine
from .diagrams import GraphMachine, TransitionGraphSupport
from .markup import MarkupMachine
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


class MachineFactory(object):
    """
        Convenience factory for machine class retrieval.
    """

    # get one of the predefined classes which fulfill the criteria
    @staticmethod
    def get_predefined(graph=False, nested=False, locked=False, asyncio=False):
        """ A function to retrieve machine classes by required functionality.
        Args:
            graph (bool): Whether the returned class should contain graph support.
            nested: Whether the returned machine class should support nested states.
            locked: Whether the returned class should facilitate locks for threadsafety.

        Returns (class): A machine class with the specified features.
        """
        try:
            return _CLASS_MAP[(graph, nested, locked, asyncio)]
        except KeyError:
            raise ValueError("Feature combination not (yet) supported")


class NestedGraphTransition(TransitionGraphSupport, NestedTransition):
    """
        A transition type to be used with (subclasses of) `HierarchicalGraphMachine` and
        `LockedHierarchicalGraphMachine`.
    """
    pass


class HierarchicalMarkupMachine(MarkupMachine, HierarchicalMachine):
    pass


class HierarchicalGraphMachine(GraphMachine, HierarchicalMarkupMachine):
    """
        A hierarchical state machine with graph support.
    """

    transition_cls = NestedGraphTransition


class LockedHierarchicalMachine(LockedMachine, HierarchicalMachine):
    """
        A threadsafe hierarchical machine.
    """

    event_cls = NestedEvent


class LockedGraphMachine(GraphMachine, LockedMachine):
    """
        A threadsafe machine with graph support.
    """
    pass


class LockedHierarchicalGraphMachine(GraphMachine, LockedMachine, HierarchicalMarkupMachine):
    """
        A threadsafe hierarchical machine with graph support.
    """

    transition_cls = NestedGraphTransition
    event_cls = NestedEvent


class AsyncGraphMachine(GraphMachine, AsyncMachine):

    transition_cls = AsyncTransition


class HierarchicalAsyncGraphMachine(GraphMachine, HierarchicalAsyncMachine):

    transition_cls = NestedAsyncTransition


# 4d tuple (graph, nested, locked, async)
_CLASS_MAP = {
    (False, False, False, False): Machine,
    (False, False, True, False): LockedMachine,
    (False, True, False, False): HierarchicalMachine,
    (False, True, True, False): LockedHierarchicalMachine,
    (True, False, False, False): GraphMachine,
    (True, False, True, False): LockedGraphMachine,
    (True, True, False, False): HierarchicalGraphMachine,
    (True, True, True, False): LockedHierarchicalGraphMachine,
    (False, False, False, True): AsyncMachine,
    (True, False, False, True): AsyncGraphMachine,
    (False, True, False, True): HierarchicalAsyncMachine,
    (True, True, False, True): HierarchicalAsyncGraphMachine
}
