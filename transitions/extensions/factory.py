"""
    transitions.extensions.factory
    ------------------------------

    This module contains the definitions of classes which combine the functionality of transitions'
    extension modules. These classes can be accessed by names as well as through a static convenience
    factory object.
"""

from ..core import Machine

from .nesting import HierarchicalMachine, NestedTransition, NestedEvent
from .locking import LockedMachine, LockedEvent
from .diagrams import GraphMachine, TransitionGraphSupport, NestedGraph


class MachineFactory(object):
    """
        Convenience factory for machine class retrieval.
    """

    # get one of the predefined classes which fulfill the criteria
    @staticmethod
    def get_predefined(graph=False, nested=False, locked=False):
        """ A function to retrieve machine classes by required functionality.
        Args:
            graph (bool): Whether the returned class should contain graph support.
            nested: Whether the returned machine class should support nested states.
            locked: Whether the returned class should facilitate locks for threadsafety.

        Returns (class): A machine class with the specified features.
        """
        return _CLASS_MAP[(graph, nested, locked)]


class NestedGraphTransition(TransitionGraphSupport, NestedTransition):
    """
        A transition type to be used with (subclasses of) `HierarchicalGraphMachine` and
        `LockedHierarchicalGraphMachine`.
    """
    pass


class LockedNestedEvent(LockedEvent, NestedEvent):
    """
        An event type to be used with (subclasses of) `LockedHierarchicalMachine`
        and `LockedHierarchicalGraphMachine`.
    """
    pass


class HierarchicalGraphMachine(GraphMachine, HierarchicalMachine):
    """
        A hierarchical state machine with graph support.
    """

    transition_cls = NestedGraphTransition
    graph_cls = NestedGraph


class LockedHierarchicalMachine(LockedMachine, HierarchicalMachine):
    """
        A threadsafe hierarchical machine.
    """

    event_cls = LockedNestedEvent


class LockedGraphMachine(GraphMachine, LockedMachine):
    """
        A threadsafe machine with graph support.
    """
    pass


class LockedHierarchicalGraphMachine(GraphMachine, LockedMachine, HierarchicalMachine):
    """
        A threadsafe hiearchical machine with graph support.
    """

    transition_cls = NestedGraphTransition
    event_cls = LockedNestedEvent
    graph_cls = NestedGraph


# 3d tuple (graph, nested, locked)
_CLASS_MAP = {
    (False, False, False): Machine,
    (False, False, True): LockedMachine,
    (False, True, False): HierarchicalMachine,
    (False, True, True): LockedHierarchicalMachine,
    (True, False, False): GraphMachine,
    (True, False, True): LockedGraphMachine,
    (True, True, False): HierarchicalGraphMachine,
    (True, True, True): LockedHierarchicalGraphMachine
}
