from transitions.extensions import MachineFactory

try:
    import asyncio
except (ImportError, SyntaxError):
    asyncio = None


from unittest.mock import MagicMock
from unittest import skipIf
from .test_core import TestTransitions, MachineError
from .utils import DummyModel
from .test_graphviz import pgv as gv
from .test_pygraphviz import pgv


@skipIf(asyncio is None, "AsyncMachine requires asyncio and contextvars suppport")
class TestAsync(TestTransitions):

    @staticmethod
    async def await_false():
        await asyncio.sleep(0.1)
        return False

    @staticmethod
    async def await_true():
        await asyncio.sleep(0.1)
        return True

    @staticmethod
    async def await_never_return():
        await asyncio.sleep(100)
        return None

    @staticmethod
    def synced_true():
        return True

    def setUp(self):
        super(TestAsync, self).setUp()
        self.machine_cls = MachineFactory.get_predefined(asyncio=True)
        self.machine = self.machine_cls(states=['A', 'B', 'C'], transitions=[['go', 'A', 'B']], initial='A')

    def test_async_machine_cb(self):
        mock = MagicMock()

        async def async_process():
            await asyncio.sleep(0.1)
            mock()

        m = self.machine
        m.after_state_change = async_process
        asyncio.run(m.go())
        self.assertEqual(m.state, 'B')
        self.assertTrue(mock.called)

    def test_async_condition(self):
        m = self.machine
        m.add_transition('proceed', 'A', 'C', conditions=self.await_true, unless=self.await_false)
        asyncio.run(m.proceed())
        self.assertEqual(m.state, 'C')

    def test_async_enter_exit(self):
        enter_mock = MagicMock()
        exit_mock = MagicMock()

        async def async_enter():
            await asyncio.sleep(0.1)
            enter_mock()

        async def async_exit():
            await asyncio.sleep(0.1)
            exit_mock()

        m = self.machine
        m.on_exit_A(async_exit)
        m.on_enter_B(async_enter)
        asyncio.run(m.go())
        self.assertTrue(exit_mock.called)
        self.assertTrue(enter_mock.called)

    def test_sync_conditions(self):
        mock = MagicMock()

        def sync_process():
            mock()

        m = self.machine
        m.add_transition('proceed', 'A', 'C', conditions=self.synced_true, after=sync_process)
        asyncio.run(m.proceed())
        self.assertEqual(m.state, 'C')
        self.assertTrue(mock.called)

    def test_multiple_models(self):
        async def fix():
            await m2.fix()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        m1 = self.machine_cls(states=['A', 'B', 'C'], initial='A', name="m1")
        m2 = self.machine_cls(states=['A', 'B', 'C'], initial='A', name="m2")
        m2.add_transition(trigger='go', source='A', dest='B', before=self.await_never_return)
        m2.add_transition(trigger='fix', source='A', dest='C', conditions=self.await_true)
        m1.add_transition(trigger='go', source='A', dest='B', conditions=self.await_true, after='go')
        m1.add_transition(trigger='go', source='B', dest='C', after=fix)
        loop.run_until_complete(asyncio.gather(m2.go(), m1.go()))
        assert m1.is_C()
        assert m2.is_C()
        loop.close()

    def test_async_callback_arguments(self):

        async def process(should_fail=True):
            if should_fail is not False:
                raise ValueError("should_fail has been set")

        self.machine.on_enter_B(process)
        with self.assertRaises(ValueError):
            asyncio.run(self.machine.go())
        asyncio.run(self.machine.to_A())
        asyncio.run(self.machine.go(should_fail=False))

    def test_async_callback_event_data(self):

        state_a = self.machine_cls.state_cls('A')
        state_b = self.machine_cls.state_cls('B')

        def sync_condition(event_data):
            return event_data.state == state_a

        async def async_conditions(event_data):
            return event_data.state == state_a

        async def async_callback(event_data):
            self.assertEqual(event_data.state, state_b)

        def sync_callback(event_data):
            self.assertEqual(event_data.state, state_b)

        m = self.machine_cls(states=[state_a, state_b], initial='A', send_event=True)
        m.add_transition('go', 'A', 'B', conditions=[sync_condition, async_conditions],
                         after=[sync_callback, async_callback])
        m.add_transition('go', 'B', 'A', conditions=sync_condition)
        asyncio.run(m.go())
        self.assertTrue(m.is_B())
        asyncio.run(m.go())
        self.assertTrue(m.is_B())

    def test_async_invalid_triggers(self):
        asyncio.run(self.machine.to_B())
        with self.assertRaises(MachineError):
            asyncio.run(self.machine.go())
        self.machine.ignore_invalid_triggers = True
        asyncio.run(self.machine.go())
        self.assertTrue(self.machine.is_B())

    def test_async_dispatch(self):
        model1 = DummyModel()
        model2 = DummyModel()
        model3 = DummyModel()

        machine = self.machine_cls(model=None, states=['A', 'B', 'C'], transitions=[['go', 'A', 'B'],
                                                                                    ['go', 'B', 'C'],
                                                                                    ['go', 'C', 'A']], initial='A')
        machine.add_model(model1)
        machine.add_model(model2, initial='B')
        machine.add_model(model3, initial='C')
        asyncio.run(machine.dispatch('go'))
        self.assertTrue(model1.is_B())
        self.assertEqual('C', model2.state)
        self.assertEqual(machine.initial, model3.state)

    def test_queued(self):
        states = ['A', 'B', 'C', 'D']
        # Define with list of dictionaries

        async def change_state(machine):
            self.assertEqual(machine.state, 'A')
            if machine.has_queue:
                await machine.run(machine=machine)
                self.assertEqual(machine.state, 'A')
            else:
                with self.assertRaises(MachineError):
                    await machine.run(machine=machine)

        async def raise_machine_error(event_data):
            self.assertTrue(event_data.machine.has_queue)
            await event_data.model.to_A()
            event_data.machine._queued = False
            await event_data.model.to_C()

        async def raise_exception(event_data):
            await event_data.model.to_C()
            raise ValueError("Clears queue")

        transitions = [
            {'trigger': 'walk', 'source': 'A', 'dest': 'B', 'before': change_state},
            {'trigger': 'run', 'source': 'B', 'dest': 'C'},
            {'trigger': 'sprint', 'source': 'C', 'dest': 'D'}
        ]

        m = self.machine_cls(states=states, transitions=transitions, initial='A')
        asyncio.run(m.walk(machine=m))
        self.assertEqual('B', m.state)
        m = self.machine_cls(states=states, transitions=transitions, initial='A', queued=True)
        asyncio.run(m.walk(machine=m))
        self.assertEqual('C', m.state)
        m = self.machine_cls(states=states, initial='A', queued=True, send_event=True,
                             before_state_change=raise_machine_error)
        with self.assertRaises(MachineError):
            asyncio.run(m.to_C())
        m = self.machine_cls(states=states, initial='A', queued=True, send_event=True)
        m.add_transition('go', 'A', 'B', after='go')
        m.add_transition('go', 'B', 'C', before=raise_exception)
        with self.assertRaises(ValueError):
            asyncio.run(m.go())
        self.assertEqual('B', m.state)


@skipIf(asyncio is None or (pgv is None and gv is None), "AsyncGraphMachine requires asyncio and (py)gaphviz")
class AsyncGraphMachine(TestAsync):

    def setUp(self):
        super(TestAsync, self).setUp()
        self.machine_cls = MachineFactory.get_predefined(graph=True, asyncio=True)
        self.machine = self.machine_cls(states=['A', 'B', 'C'], transitions=[['go', 'A', 'B']], initial='A')


class TestHierarchicalAsync(TestAsync):

    def setUp(self):
        super(TestAsync, self).setUp()
        self.machine_cls = MachineFactory.get_predefined(nested=True, asyncio=True)
        self.machine = self.machine_cls(states=['A', 'B', 'C'], transitions=[['go', 'A', 'B']], initial='A')

    def test_nested_async(self):
        mock = MagicMock()

        async def sleep_mock():
            await asyncio.sleep(0.1)
            mock()

        states = ['A', 'B', {'name': 'C', 'children': ['1', {'name': '2', 'children': ['a', 'b'], 'initial': 'a'},
                                                       '3'], 'initial': '2'}]
        transitions = [{'trigger': 'go', 'source': 'A', 'dest': 'C',
                        'after': [sleep_mock] * 100}]
        machine = self.machine_cls(states=states, transitions=transitions, initial='A')
        asyncio.run(machine.go())
        self.assertEqual('C{0}2{0}a'.format(machine.state_cls.separator), machine.state)
        self.assertEqual(100, mock.call_count)

    def test_parallel_async(self):
        states = ['A', 'B', {'name': 'P',
                             'parallel': [
                                 {'name': '1', 'children': ['a'], 'initial': 'a'},
                                 {'name': '2', 'children': ['b', 'c'], 'initial': 'b'},
                                 {'name': '3', 'children': ['x', 'y', 'z'], 'initial': 'y'}]}]
        machine = self.machine_cls(states=states, initial='A')
        asyncio.run(machine.to_P())
        self.assertEqual(['P{0}1{0}a'.format(machine.state_cls.separator),
                          'P{0}2{0}b'.format(machine.state_cls.separator),
                          'P{0}3{0}y'.format(machine.state_cls.separator)], machine.state)
