from typing import TYPE_CHECKING
from unittest import TestCase
from types import ModuleType
from unittest.mock import MagicMock

from transitions import Machine
from transitions.experimental.utils import generate_base_model
from transitions.extensions import HierarchicalMachine

from .utils import Stuff

if TYPE_CHECKING:
    from transitions.core import MachineConfig
    from typing import Type


def import_code(code: str, name: str) -> ModuleType:
    module = ModuleType(name)
    exec(code, module.__dict__)
    return module


class TestExperimental(TestCase):

    def setUp(self) -> None:
        self.machine_cls = Machine  # type: Type[Machine]

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
            model.to_B()  # type: ignore # Should not be assigned to model since its not declared
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


class TestHSMExperimental(TestExperimental):

    def setUp(self):
        self.machine_cls = HierarchicalMachine  # type: Type[HierarchicalMachine]
        self.create_trigger_class()
