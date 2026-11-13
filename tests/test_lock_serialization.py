"""Regression tests for locked-machine model/context serialization."""
import copy
import pickle

import pytest

from transitions.extensions import LockedHierarchicalMachine, LockedMachine


class UnhashableModel:
    def __eq__(self, other):
        return self is other


class RecordingContext:
    def __init__(self):
        self.entries = 0
        self.depth = 0

    def __enter__(self):
        self.entries += 1
        self.depth += 1

    def __exit__(self, *exc):
        self.depth -= 1


def pickle_roundtrip(machine):
    return pickle.loads(pickle.dumps(machine))


@pytest.mark.parametrize('machine_cls', [LockedMachine, LockedHierarchicalMachine])
@pytest.mark.parametrize('restore', [copy.deepcopy, pickle_roundtrip])
@pytest.mark.parametrize('model_count', [1, 2])
def test_unhashable_models_keep_contexts_after_serialization(machine_cls, restore, model_count):
    models = [UnhashableModel() for _ in range(model_count)]
    shared = RecordingContext()
    contexts = [RecordingContext() for _ in models]
    machine = machine_cls(model=[], states=['A', 'B'], initial='A', machine_context=shared)
    for model, context in zip(models, contexts):
        machine.add_model(model, model_context=context)
    models[0].to_B()

    restored = restore(machine)
    assert restored is not machine
    assert restored.models[0].state == 'B'
    restored_shared = restored.machine_context[0]
    assert restored_shared is not shared
    for index, model in enumerate(restored.models):
        assert model is not models[index]
        model_contexts = restored.model_context_map[id(model)]
        assert model_contexts[0] is restored_shared
        assert model_contexts[1] is restored._ident
        private = model_contexts[2]
        assert private is not contexts[index]
        original_entries = contexts[index].entries
        before = private.entries
        model.to_A()
        model.to_B()
        assert model.state == 'B'
        # Nested-machine triggers currently use the machine context, not model contexts.
        if machine_cls is LockedMachine:
            assert private.entries == before + 2
        else:
            assert private.entries == before
        assert private.depth == 0
        assert restored_shared.depth == 0
        assert contexts[index].entries == original_entries
    if model_count == 2:
        assert restored.model_context_map[id(restored.models[0])][2] is not restored.model_context_map[id(restored.models[1])][2]
    assert models[0].state == 'B'
    assert shared.depth == 0
    if model_count == 2:
        assert models[1].state == 'A'


@pytest.mark.parametrize('machine_cls', [LockedMachine, LockedHierarchicalMachine])
def test_restore_legacy_hash_keyed_model_contexts(machine_cls):
    machine = machine_cls(states=['A', 'B'], initial='A')
    state = machine.__getstate__()
    state['_model_context_map_store'] = {model: machine.model_context_map[id(model)] for model in machine.models}
    machine.__setstate__(state)
    machine.to_B()
    assert machine.state == 'B'
    assert machine.model_context_map[id(machine)][-1] is machine._ident


class UnhashableLockedMachine(LockedMachine):
    def __eq__(self, other):
        return self is other


class UnhashableLockedHierarchicalMachine(LockedHierarchicalMachine):
    def __eq__(self, other):
        return self is other


@pytest.mark.parametrize('machine_cls', [UnhashableLockedMachine, UnhashableLockedHierarchicalMachine])
@pytest.mark.parametrize('restore', [copy.deepcopy, pickle_roundtrip])
def test_unhashable_self_model_gets_independent_lock(machine_cls, restore):
    machine = machine_cls(states=['A', 'B'], initial='A')
    machine.to_B()
    restored = restore(machine)
    assert restored.models[0] is restored
    assert restored.model_context_map[id(restored)][-1] is restored._ident
    original_lock = machine.machine_context[0].lock
    restored_lock = restored.machine_context[0].lock
    assert restored_lock is not original_lock
    assert original_lock.acquire(False)
    try:
        assert restored_lock.acquire(False)
        restored_lock.release()
        restored.to_A()
        assert restored.state == 'A'
        assert machine.state == 'B'
    finally:
        original_lock.release()
