from typing import TYPE_CHECKING, Sequence, Union, List
from unittest import TestCase
from types import ModuleType
from unittest.mock import MagicMock

from transitions import Machine
from transitions.experimental.utils import generate_base_model
from transitions.experimental.utils import add_transitions, transition, event, with_model_definitions
from transitions.extensions import HierarchicalMachine

from .utils import Stuff

if TYPE_CHECKING:
    from transitions.core import MachineConfig, TransitionConfig
    from typing import Type


def import_code(code: str, name: str) -> ModuleType:
    module = ModuleType(name)
    exec(code, module.__dict__)
    return module


class TestExperimental(TestCase):

    def setUp(self) -> None:
        self.machine_cls = Machine  # type: Type[Machine]
        self.create_trigger_class()

    def create_trigger_class(self):
        @with_model_definitions
        class TriggerMachine(self.machine_cls):  # type: ignore
            pass

        self.trigger_machine = TriggerMachine

    def test_model_override(self):

        class Model:

            def trigger(self, name: str) -> bool:
                raise RuntimeError("Should be overridden")

            def is_A(self) -> bool:
                raise RuntimeError("Should be overridden")

            def is_C(self) -> bool:
                raise RuntimeError("Should be overridden")

        model = Model()
        machine = self.machine_cls(model, states=["A", "B"], initial="A", model_override=True)
        self.assertTrue(model.is_A())
        with self.assertRaises(AttributeError):
            model.to_B()  # Should not be assigned to model since its not declared
        self.assertTrue(model.trigger("to_B"))
        self.assertFalse(model.is_A())
        with self.assertRaises(RuntimeError):
            model.is_C()  # not overridden yet
        machine.add_state("C")
        self.assertFalse(model.is_C())  # now it is!
        self.assertTrue(model.trigger("to_C"))
        self.assertTrue(model.is_C())

    def test_generate_base_model(self):
        simple_config = {
            "states": ["A", "B"],
            "transitions": [
                ["go", "A", "B"],
                ["back", "*", "A"]
            ],
            "initial": "A",
            "model_override": True
        }  # type: MachineConfig

        mod = import_code(generate_base_model(simple_config), "base_module")
        model = mod.BaseModel()
        machine = self.machine_cls(model, **simple_config)
        self.assertTrue(model.is_A())
        self.assertTrue(model.go())
        self.assertTrue(model.is_B())
        self.assertTrue(model.back())
        self.assertTrue(model.state == "A")
        with self.assertRaises(AttributeError):
            model.is_C()

    def test_generate_base_model_callbacks(self):
        simple_config = {
            "states": ["A", "B"],
            "transitions": [
                ["go", "A", "B"],
            ],
            "initial": "A",
            "model_override": True,
            "before_state_change": "call_this"
        }  # type: MachineConfig

        mod = import_code(generate_base_model(simple_config), "base_module")
        mock = MagicMock()

        class Model(mod.BaseModel):  # type: ignore

            @staticmethod
            def call_this() -> None:
                mock()

        model = Model()
        machine = self.machine_cls(model, **simple_config)
        self.assertTrue(model.is_A())
        self.assertTrue(model.go())
        self.assertTrue(mock.called)

    def test_generate_model_no_auto(self):
        simple_config: MachineConfig = {
            "states": ["A", "B"],
            "auto_transitions": False,
            "model_override": True,
            "transitions": [
                ["go", "A", "B"],
                ["back", "*", "A"]
            ],
            "initial": "A"
        }
        mod = import_code(generate_base_model(simple_config), "base_module")
        model = mod.BaseModel()
        machine = self.machine_cls(model, **simple_config)
        self.assertTrue(model.is_A())
        self.assertTrue(model.go())
        with self.assertRaises(AttributeError):
            model.to_B()

    def test_decorator(self):

        class Model:

            state: str = ""

            def is_B(self) -> bool:
                return False

            @add_transitions(transition(source="A", dest="B"))
            @add_transitions([["A", "B"], "C"])
            def go(self) -> bool:
                raise RuntimeError("Should be overridden!")

        model = Model()
        machine = self.trigger_machine(model, states=["A", "B", "C"], initial="A")
        self.assertEqual("A", model.state)
        self.assertTrue(machine.is_state("A", model))
        self.assertTrue(model.go())
        with self.assertRaises(AttributeError):
            model.is_A()
        self.assertEqual("B", model.state)
        self.assertTrue(model.is_B())
        self.assertTrue(model.go())
        self.assertFalse(model.is_B())
        self.assertEqual("C", model.state)

    def test_decorator_complex(self):

        class Model:

            state: str = ""

            def check_param(self, param: bool) -> bool:
                return param

            @add_transitions(transition(source="A", dest="B"),
                             transition(source="B", dest="C", unless=Stuff.this_passes),
                             transition(source="B", dest="A", conditions=Stuff.this_passes, unless=Stuff.this_fails))
            def go(self) -> bool:
                raise RuntimeError("Should be overridden")

            @add_transitions({"source": "A", "dest": "B", "conditions": "check_param"})
            def event(self, param) -> bool:
                raise RuntimeError("Should be overridden")

        model = Model()
        machine = self.trigger_machine(model, states=["A", "B"], initial="A")
        self.assertTrue(model.go())
        self.assertTrue(model.state == "B")
        self.assertTrue(model.go())
        self.assertTrue(model.state == "A")
        self.assertFalse(model.event(param=False))
        self.assertTrue(model.state == "A")
        self.assertTrue(model.event(param=True))
        self.assertTrue(model.state == "B")

    def test_event_definition(self):

        class Model:

            state: str = ""

            def is_B(self) -> bool:
                return False

            go = event(transition(source="A", dest="B"), [["A", "B"], "C"], {"source": "*", "dest": None})

        model = Model()
        machine = self.trigger_machine(model, states=["A", "B", "C"], initial="A")
        self.assertEqual("A", model.state)
        self.assertTrue(machine.is_state("A", model))
        self.assertTrue(model.go())
        with self.assertRaises(AttributeError):
            model.is_A()
        self.assertEqual("B", model.state)
        self.assertTrue(model.is_B())
        self.assertTrue(model.go())
        self.assertFalse(model.is_B())
        self.assertEqual("C", model.state)

    def test_event_definition_complex(self):

        class Model:

            state: str = ""

            go = event(transition(source="A", dest="B"),
                       transition(source="B", dest="C", unless=Stuff.this_passes),
                       transition(source="B", dest="A", conditions=Stuff.this_passes, unless=Stuff.this_fails))

            event = event({"source": "A", "dest": "B", "conditions": "check_param"})

            def check_param(self, param: bool) -> bool:
                return param

        model = Model()
        machine = self.trigger_machine(model, states=["A", "B"], initial="A")
        self.assertTrue(model.go())
        self.assertTrue(model.state == "B")
        self.assertTrue(model.go())
        self.assertTrue(model.state == "A")
        self.assertFalse(model.event(param=False))
        self.assertTrue(model.state == "A")
        self.assertTrue(model.event(param=True))
        self.assertTrue(model.state == "B")


class TestHSMExperimental(TestExperimental):

    def setUp(self):
        self.machine_cls = HierarchicalMachine  # type: Type[HierarchicalMachine]
        self.create_trigger_class()
