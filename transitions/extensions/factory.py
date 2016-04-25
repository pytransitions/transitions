from ..core import Machine

from .nesting import HierarchicalMachine, NestedTransition, NestedEvent
from .locking import LockedMachine, LockedEvent
from .diagrams import GraphMachine, TransitionGraphSupport


class MachineFactory(object):

    # get one of the predefined classes which fulfill the criteria
    @staticmethod
    def get_predefined(graph=False, nested=False, locked=False):
        if graph and nested and locked:
            return LockedHierarchicalGraphMachine
        elif locked and nested:
            return LockedHierarchicalMachine
        elif locked and graph:
            return LockedGraphMachine
        elif nested and graph:
            return HierarchicalGraphMachine
        elif graph:
            return GraphMachine
        elif nested:
            return HierarchicalMachine
        elif locked:
            return LockedMachine
        else:
            return Machine


class NestedGraphTransition(TransitionGraphSupport, NestedTransition):
    pass


class LockedNestedEvent(LockedEvent, NestedEvent):
    pass


class HierarchicalGraphMachine(GraphMachine, HierarchicalMachine):

    @staticmethod
    def _create_transition(*args, **kwargs):
        return NestedGraphTransition(*args, **kwargs)


class LockedHierarchicalMachine(LockedMachine, HierarchicalMachine):

    @staticmethod
    def _create_event(*args, **kwargs):
        return LockedNestedEvent(*args, **kwargs)


class LockedGraphMachine(GraphMachine, LockedMachine):
    pass


class LockedHierarchicalGraphMachine(GraphMachine, LockedMachine, HierarchicalMachine):

    @staticmethod
    def _create_transition(*args, **kwargs):
        return NestedGraphTransition(*args, **kwargs)

    @staticmethod
    def _create_event(*args, **kwargs):
        return LockedNestedEvent(*args, **kwargs)
