from transitions.extensions import MachineFactory

try:
    import asyncio
except (ImportError, SyntaxError):
    asyncio = None


from unittest.mock import MagicMock
from unittest import skipIf
from functools import partial
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
    async def cancel_soon():
        await asyncio.sleep(1)
        raise TimeoutError("Callback was not cancelled!")

    @staticmethod
    def raise_value_error():
        raise ValueError("ValueError raised.")

    @staticmethod
    def synced_true():
        return True

    @staticmethod
    async def call_delayed(func, time):
        await asyncio.sleep(time)
        await func()

    def setUp(self):
        super(TestAsync, self).setUp()
        self.machine_cls = MachineFactory.get_predefined(asyncio=True)
        self.machine = self.machine_cls(states=['A', 'B', 'C'], transitions=[['go', 'A', 'B']], initial='A')

    def test_new_state_in_enter_callback(self):
        machine = self.machine_cls(states=['A', 'B'], initial='A')

        async def on_enter_B():
            state = self.machine_cls.state_cls(name='C')
            machine.add_state(state)
            await machine.to_C()

        machine.on_enter_B(on_enter_B)
        asyncio.run(machine.to_B())

    def test_dynamic_model_state_attribute(self):
        class Model:
            def __init__(self):
                self.status = None
                self.state = 'some_value'

        m = self.machine_cls(Model(), states=['A', 'B'], initial='A', model_attribute='status')
        self.assertEqual(m.model.status, 'A')
        self.assertEqual(m.model.state, 'some_value')

        m.add_transition('move', 'A', 'B')
        asyncio.run(m.model.move())

        self.assertEqual(m.model.status, 'B')
        self.assertEqual(m.model.state, 'some_value')

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
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        m1 = self.machine_cls(states=['A', 'B', 'C'], initial='A', name="m1")
        m2 = self.machine_cls(states=['A'], initial='A', name='m2')
        m1.add_transition(trigger='go', source='A', dest='B', before=self.cancel_soon)
        m1.add_transition(trigger='fix', source='A', dest='C', after=self.cancel_soon)
        m1.add_transition(trigger='check', source='C', dest='B', conditions=self.await_false)
        m1.add_transition(trigger='reset', source='C', dest='A')
        m2.add_transition(trigger='go', source='A', dest=None, conditions=m1.is_C, after=m1.reset)

        loop.run_until_complete(asyncio.gather(m1.go(),  # should block before B
                                               self.call_delayed(m1.fix, 0.05),  # should cancel task and go to C
                                               self.call_delayed(m1.check, 0.07),  # should exit before m1.fix
                                               self.call_delayed(m2.go, 0.1)))  # should cancel m1.fix
        assert m1.is_A()
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

    def test_model_queue(self):
        mock = MagicMock()

        def check_mock():
            self.assertTrue(mock.called)

        m1 = DummyModel()
        m2 = DummyModel()

        async def run():
            transitions = [{'trigger': 'mock', 'source': ['A', 'B'], 'dest': 'B', 'after': mock},
                           {'trigger': 'delayed', 'source': 'A', 'dest': 'B', 'before': partial(asyncio.sleep, 0.1)},
                           {'trigger': 'check', 'source': 'B', 'dest': 'A', 'after': check_mock},
                           {'trigger': 'error', 'source': 'B', 'dest': 'C', 'before': self.raise_value_error}]
            m = self.machine_cls(model=[m1, m2], states=['A', 'B', 'C'], transitions=transitions, initial='A',
                                 queued='model')
            # call m1.delayed and m2.mock should be called immediately
            # m1.check should be delayed until after m1.delayed
            await asyncio.gather(m1.delayed(), self.call_delayed(m1.check, 0.02), self.call_delayed(m2.mock, 0.04))
            self.assertTrue(m1.is_A())
            self.assertTrue(m2.is_B())
            mock.reset_mock()
            with self.assertRaises(ValueError):
                # m1.error raises an error which should cancel m1.to_A but not m2.mock and m2.check
                await asyncio.gather(m1.to_A(), m2.to_A(),
                                     self.call_delayed(m1.delayed, 0.01), self.call_delayed(m2.delayed, 0.01),
                                     self.call_delayed(m1.error, 0.02), self.call_delayed(m1.to_A, 0.03),
                                     self.call_delayed(m2.mock, 0.03), self.call_delayed(m2.check, 0.04))
            await asyncio.sleep(0.05)  # give m2 events time to finish
            self.assertTrue(m1.is_B())
            self.assertTrue(m2.is_A())
        asyncio.run(run())

    def test_queued_remove(self):

        def remove_model(event_data):
            event_data.machine.remove_model(event_data.model)

        def check_queue(expect, event_data):
            self.assertEqual(expect, len(event_data.machine._transition_queue_dict[event_data.model]))

        transitions = [
            {'trigger': 'go', 'source': 'A', 'dest': 'B', 'after': partial(asyncio.sleep, 0.1)},
            {'trigger': 'go', 'source': 'B', 'dest': 'C'},
            {'trigger': 'remove', 'source': 'B', 'dest': None, 'prepare': ['to_A', 'to_C'],
             'before': partial(check_queue, 4), 'after': remove_model},
            {'trigger': 'remove_queue', 'source': 'B', 'dest': None, 'prepare': ['to_A', 'to_C'],
             'before': partial(check_queue, 3), 'after': remove_model}
        ]

        async def run():
            m1 = DummyModel()
            m2 = DummyModel()
            m = self.machine_cls(model=[m1, m2], states=['A', 'B', 'C'], transitions=transitions,
                                 initial='A', queued=True, send_event=True)
            await asyncio.gather(m1.go(), m2.go(),
                                 self.call_delayed(m1.remove, 0.02), self.call_delayed(m2.go, 0.04))
            _ = repr(m._transition_queue_dict)  # check whether _DictionaryMock returns a valid representation
            self.assertTrue(m1.is_B())
            self.assertTrue(m2.is_C())
            m.remove_model(m2)
            self.assertNotIn(m1, m._transition_queue_dict)
            self.assertNotIn(m2, m._transition_queue_dict)
            m1 = DummyModel()
            m2 = DummyModel()
            m = self.machine_cls(model=[m1, m2], states=['A', 'B', 'C'], transitions=transitions,
                                 initial='A', queued='model', send_event=True)
            await asyncio.gather(m1.go(), m2.go(),
                                 self.call_delayed(m1.remove_queue, 0.02), self.call_delayed(m2.go, 0.04))
            self.assertTrue(m1.is_B())
            self.assertTrue(m2.is_C())
            m.remove_model(m2)
        asyncio.run(run())

    def test_async_timeout(self):
        from transitions.extensions.states import add_state_features
        from transitions.extensions.asyncio import AsyncTimeout

        timeout_called = MagicMock()

        @add_state_features(AsyncTimeout)
        class TimeoutMachine(self.machine_cls):
            pass

        states = ['A', {'name': 'B', 'timeout': 0.2, 'on_timeout': ['to_C', timeout_called]}, 'C']
        m = TimeoutMachine(states=states, initial='A')
        with self.assertRaises(AttributeError):
            m.add_state('Fail', timeout=1)

        async def run():
            await m.to_B()
            await asyncio.sleep(0.1)
            self.assertTrue(m.is_B())  # timeout shouldn't be triggered
            await m.to_A()  # cancel timeout
            self.assertTrue(m.is_A())
            await m.to_B()
            await asyncio.sleep(0.3)
            self.assertTrue(m.is_C())  # now timeout should have been processed
            self.assertTrue(timeout_called.called)
        asyncio.run(run())

    def test_callback_order(self):
        finished = []

        class Model:
            async def before(self):
                await asyncio.sleep(0.1)
                finished.append(2)

            async def after(self):
                await asyncio.sleep(0.1)
                finished.append(3)

        async def after_state_change():
            finished.append(4)

        async def before_state_change():
            finished.append(1)

        model = Model()
        m = self.machine_cls(
            model=model,
            states=['start', 'end'],
            after_state_change=after_state_change,
            before_state_change=before_state_change,
            initial='start',
        )
        m.add_transition('transit', 'start', 'end', after='after', before='before')
        asyncio.run(model.transit())
        assert finished == [1, 2, 3, 4]

    def test_task_cleanup(self):

        models = [DummyModel() for i in range(100)]
        m = self.machine_cls(model=models, states=['A', 'B'], initial='A')
        self.assertEqual(0, len(m.async_tasks))  # check whether other tests were already leaking tasks

        async def run():
            for model in m.models:
                await model.to_B()

        asyncio.run(run())
        self.assertEqual(0, len(m.async_tasks))

    def test_on_exception_callback(self):
        mock = MagicMock()

        def on_exception(event_data):
            self.assertIsInstance(event_data.error, ValueError)
            mock()

        m = self.machine_cls(states=['A', 'B'], initial='A', send_event=True,
                             after_state_change=partial(self.stuff.this_raises, ValueError))

        async def run():
            with self.assertRaises(ValueError):
                await m.to_B()

            m.on_exception.append(on_exception)
            await m.to_B()
            self.assertTrue(mock.called)

        asyncio.run(run())


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
        asyncio.run(machine.to_B())
        self.assertTrue(machine.is_B())


@skipIf(asyncio is None or (pgv is None and gv is None), "AsyncGraphMachine requires asyncio and (py)gaphviz")
class AsyncHierarchicalGraphMachine(TestHierarchicalAsync):

    def setUp(self):
        super(TestHierarchicalAsync, self).setUp()
        self.machine_cls = MachineFactory.get_predefined(graph=True, asyncio=True, nested=True)
        self.machine = self.machine_cls(states=['A', 'B', 'C'], transitions=[['go', 'A', 'B']], initial='A')
