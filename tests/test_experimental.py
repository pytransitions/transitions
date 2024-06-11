from unittest import TestCase
from unittest.mock import MagicMock

from transitions import Machine
from transitions.experimental.decoration import expect_override


class TestExperimental(TestCase):

    def setUp(self) -> None:
        self.machine_cls = Machine
        return super().setUp()

    def test_override_decorator(self):
        b_mock = MagicMock()
        c_mock = MagicMock()

        class Model:

            @expect_override
            def is_A(self) -> bool:
                raise RuntimeError("Should be overridden")

            def is_B(self) -> bool:
                b_mock()
                return False

            @expect_override
            def is_C(self) -> bool:
                c_mock()
                return False

        model = Model()
        machine = self.machine_cls(model, states=["A", "B"], initial="A")
        self.assertTrue(model.is_A())
        self.assertTrue(model.to_B())
        self.assertFalse(model.is_B())  # not overridden with convenience function
        self.assertTrue(b_mock.called)
        self.assertFalse(model.is_C())  # not overridden yet
        self.assertTrue(c_mock.called)
        machine.add_state("C")
        self.assertFalse(model.is_C())  # now it is!
        self.assertEqual(1, c_mock.call_count)   # call_count is not increased
        self.assertTrue(model.to_C())
        self.assertTrue(model.is_C())
        self.assertEqual(1, c_mock.call_count)
