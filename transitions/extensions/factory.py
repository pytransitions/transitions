"""
    transitions.extensions.factory
    ------------------------------

    This module contains the definitions of classes which combine the functionality of transitions'
    extension modules. These classes can be accessed by names as well as through a static convenience
    factory object.
"""

from functools import partial

from ..core import Machine, Transition

from .nesting import HierarchicalMachine, NestedEvent, NestedTransition
from .locking import LockedMachine
from .diagrams import GraphMachine, NestedGraphTransition, HierarchicalGraphMachine

try:
    from transitions.extensions.asyncio import AsyncMachine, AsyncTransition
    from transitions.extensions.asyncio import HierarchicalAsyncMachine, NestedAsyncTransition
except (ImportError, SyntaxError):
    class AsyncMachine(Machine):  # type: ignore
        """ A mock of AsyncMachine for Python 3.6 and earlier. """

    class AsyncTransition(Transition):  # type: ignore
        """ A mock of AsyncTransition for Python 3.6 and earlier. """

    class HierarchicalAsyncMachine(HierarchicalMachine):  # type: ignore
        """ A mock of HierarchicalAsyncMachine for Python 3.6 and earlier. """

    class NestedAsyncTransition(NestedTransition):  # type: ignore
        """ A mock of NestedAsyncTransition for Python 3.6 and earlier. """


class MachineFactory(object):
    """ Convenience factory for machine class retrieval. """

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
            raise ValueError("Feature combination not (yet) supported")  # from KeyError


class LockedHierarchicalMachine(LockedMachine, HierarchicalMachine):
    """
        A threadsafe hierarchical machine.
    """

    event_cls = NestedEvent

    def _get_qualified_state_name(self, state):
        return self.get_global_name(state.name)


class LockedGraphMachine(GraphMachine, LockedMachine):
    """
        A threadsafe machine with graph support.
    """

    @staticmethod
    def format_references(func):
        if isinstance(func, partial) and func.func.__name__.startswith('_locked_method'):
            func = func.args[0]
        return GraphMachine.format_references(func)


class LockedHierarchicalGraphMachine(GraphMachine, LockedHierarchicalMachine):
    """
        A threadsafe hierarchical machine with graph support.
    """

    transition_cls = NestedGraphTransition
    event_cls = NestedEvent

    @staticmethod
    def format_references(func):
        if isinstance(func, partial) and func.func.__name__.startswith('_locked_method'):
            func = func.args[0]
        return GraphMachine.format_references(func)


class AsyncGraphMachine(GraphMachine, AsyncMachine):
    """ A machine that supports asynchronous event/callback processing with Graphviz support. """

    transition_cls = AsyncTransition


class HierarchicalAsyncGraphMachine(GraphMachine, HierarchicalAsyncMachine):
    """ A hierarchical machine that supports asynchronous event/callback processing with Graphviz support. """

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
