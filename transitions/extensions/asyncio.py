import itertools
import logging
import asyncio
import contextvars
import inspect

from functools import partial, reduce
import copy

from ..core import State, Condition, Transition, EventData, listify
from ..core import Event, MachineError, Machine
from .nesting import HierarchicalMachine, NestedState, NestedEvent, NestedTransition, _resolve_order


_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


class AsyncState(State):
    """A persistent representation of a state managed by a ``Machine``. Callback execution is done asynchronously.

    Attributes:
        name (str): State name which is also assigned to the model(s).
        on_enter (list): Callbacks awaited when a state is entered.
        on_exit (list): Callbacks awaited when a state is entered.
        ignore_invalid_triggers (bool): Indicates if unhandled/invalid triggers should raise an exception.
    """

    async def enter(self, event_data):
        """ Triggered when a state is entered. """
        _LOGGER.debug("%sEntering state %s. Processing callbacks...", event_data.machine.name, self.name)
        await event_data.machine.callbacks(self.on_enter, event_data)
        _LOGGER.info("%sEntered state %s", event_data.machine.name, self.name)

    async def exit(self, event_data):
        """ Triggered when a state is exited. """
        _LOGGER.debug("%sExiting state %s. Processing callbacks...", event_data.machine.name, self.name)
        await event_data.machine.callbacks(self.on_exit, event_data)
        _LOGGER.info("%sExited state %s", event_data.machine.name, self.name)


class NestedAsyncState(NestedState, AsyncState):

    async def scoped_enter(self, event_data, scope=[]):
        self._scope = scope
        await self.enter(event_data)
        self._scope = []

    async def scoped_exit(self, event_data, scope=[]):
        self._scope = scope
        await self.exit(event_data)
        self._scope = []


class AsyncCondition(Condition):
    """ A helper class to await condition checks in the intended way.

    Attributes:
        func (callable): The function to call for the condition check
        target (bool): Indicates the target state--i.e., when True,
                the condition-checking callback should return True to pass,
                and when False, the callback should return False to pass.
    """

    async def check(self, event_data):
        """ Check whether the condition passes.
        Args:
            event_data (EventData): An EventData instance to pass to the
                condition (if event sending is enabled) or to extract arguments
                from (if event sending is disabled). Also contains the data
                model attached to the current machine which is used to invoke
                the condition.
        """
        func = event_data.machine.resolve_callable(self.func, event_data)
        res = func(event_data) if event_data.machine.send_event else func(*event_data.args, **event_data.kwargs)
        if inspect.isawaitable(res):
            return await res == self.target
        return res == self.target


class AsyncTransition(Transition):
    """ Representation of an asynchronous transition managed by a ``AsyncMachine`` instance.

    Attributes:
        source (str): Source state of the transition.
        dest (str): Destination state of the transition.
        prepare (list): Callbacks executed before conditions checks.
        conditions (list): Callbacks evaluated to determine if
            the transition should be executed.
        before (list): Callbacks executed before the transition is executed
            but only if condition checks have been successful.
        after (list): Callbacks executed after the transition is executed
            but only if condition checks have been successful.
    """

    condition_cls = AsyncCondition

    async def _eval_conditions(self, event_data):
        res = await event_data.machine.await_all([partial(cond.check, event_data) for cond in self.conditions])
        if not all(res):
            _LOGGER.debug("%sTransition condition failed: Transition halted.", event_data.machine.name)
            return False
        return True

    async def execute(self, event_data):
        """ Executes the transition.
        Args:
            event_data: An instance of class EventData.
        Returns: boolean indicating whether or not the transition was
            successfully executed (True if successful, False if not).
        """
        _LOGGER.debug("%sInitiating transition from state %s to state %s...",
                      event_data.machine.name, self.source, self.dest)

        await event_data.machine.callbacks(self.prepare, event_data)
        _LOGGER.debug("%sExecuted callbacks before conditions.", event_data.machine.name)

        if not await self._eval_conditions(event_data):
            return False

        machine = event_data.machine
        # cancel running tasks since the transition will happen
        machine.switch_model_context(event_data.model)

        await event_data.machine.callbacks(itertools.chain(event_data.machine.before_state_change, self.before), event_data)
        _LOGGER.debug("%sExecuted callback before transition.", event_data.machine.name)

        if self.dest:  # if self.dest is None this is an internal transition with no actual state change
            await self._change_state(event_data)

        await event_data.machine.callbacks(itertools.chain(self.after, event_data.machine.after_state_change), event_data)
        _LOGGER.debug("%sExecuted callback after transition.", event_data.machine.name)
        return True

    async def _change_state(self, event_data):
        if hasattr(event_data.machine, "model_graphs"):
            graph = event_data.machine.model_graphs[event_data.model]
            graph.reset_styling()
            graph.set_previous_transition(self.source, self.dest)
        await event_data.machine.get_state(self.source).exit(event_data)
        event_data.machine.set_state(self.dest, event_data.model)
        event_data.update(event_data.model.state)
        await event_data.machine.get_state(self.dest).enter(event_data)


class NestedAsyncTransition(AsyncTransition, NestedTransition):

    async def _change_state(self, event_data):
        if hasattr(event_data.machine, "model_graphs"):
            graph = event_data.machine.model_graphs[event_data.model]
            graph.reset_styling()
            graph.set_previous_transition(self.source, self.dest)
        state_tree, exit_partials, enter_partials = self._resolve_transition(event_data)
        for func in exit_partials:
            await func()
        self._update_model(event_data, state_tree)
        for func in enter_partials:
            await func()


class AsyncEvent(Event):
    """ A collection of transitions assigned to the same trigger """

    async def trigger(self, _model, *args, **kwargs):
        """ Serially execute all transitions that match the current state,
        halting as soon as one successfully completes. Note that `AsyncEvent` triggers must be awaited.
        Args:
            args and kwargs: Optional positional or named arguments that will
                be passed onto the EventData object, enabling arbitrary state
                information to be passed on to downstream triggered functions.
        Returns: boolean indicating whether or not a transition was
            successfully executed (True if successful, False if not).
        """
        func = partial(self._trigger, _model, *args, **kwargs)
        return await self.machine.process_context(func, _model)

    async def _trigger(self, model, *args, **kwargs):
        state = self.machine.get_state(model.state)
        if state.name not in self.transitions:
            msg = "%sCan't trigger event %s from state %s!" % (self.machine.name, self.name,
                                                               state.name)
            ignore = state.ignore_invalid_triggers if state.ignore_invalid_triggers is not None \
                else self.machine.ignore_invalid_triggers
            if ignore:
                _LOGGER.warning(msg)
                return False
            else:
                raise MachineError(msg)
        event_data = EventData(state, self, self.machine, model, args=args, kwargs=kwargs)
        return await self._process(event_data)

    async def _process(self, event_data):
        await self.machine.callbacks(self.machine.prepare_event, event_data)
        _LOGGER.debug("%sExecuted machine preparation callbacks before conditions.", self.machine.name)

        try:
            for trans in self.transitions[event_data.state.name]:
                event_data.transition = trans
                if await trans.execute(event_data):
                    event_data.result = True
                    break
        except Exception as err:
            event_data.error = err
            raise
        finally:
            await self.machine.callbacks(self.machine.finalize_event, event_data)
            _LOGGER.debug("%sExecuted machine finalize callbacks", self.machine.name)
        return event_data.result


class NestedAsyncEvent(NestedEvent):

    async def trigger(self, _model, _machine, *args, **kwargs):
        """ Serially execute all transitions that match the current state,
        halting as soon as one successfully completes. NOTE: This should only
        be called by HierarchicalMachine instances.
        Args:
            _model (object): model object to
            _machine (HierarchicalMachine): Since NestedEvents can be used in multiple machine instances, this one
                                            will be used to determine the current state separator.
            args and kwargs: Optional positional or named arguments that will
                be passed onto the EventData object, enabling arbitrary state
                information to be passed on to downstream triggered functions.
        Returns: boolean indicating whether or not a transition was
            successfully executed (True if successful, False if not).
        """
        func = partial(self._trigger, _model, _machine, *args, **kwargs)
        return await _machine.process_context(func, _model)

    async def _trigger(self, _model, _machine, *args, **kwargs):
        state_tree = _machine._build_state_tree(getattr(_model, _machine.model_attribute), _machine.state_cls.separator)
        state_tree = reduce(dict.get, _machine.get_global_name(join=False), state_tree)
        ordered_states = _resolve_order(state_tree)
        done = set()
        res = None
        for state_path in ordered_states:
            state_name = _machine.state_cls.separator.join(state_path)
            if state_name not in done and state_name in self.transitions:
                state = _machine.get_state(state_name)
                event_data = EventData(state, self, _machine, _model, args=args, kwargs=kwargs)
                event_data.source_name = state_name
                event_data.source_path = copy.copy(state_path)
                res = await self._process(event_data)
                if res:
                    elems = state_path
                    while elems:
                        done.add(_machine.state_cls.separator.join(elems))
                        elems.pop()
        return res

    async def _process(self, event_data):
        machine = event_data.machine
        await machine.callbacks(event_data.machine.prepare_event, event_data)
        _LOGGER.debug("%sExecuted machine preparation callbacks before conditions.", machine.name)

        try:
            for trans in self.transitions[event_data.source_name]:
                event_data.transition = trans
                if await trans.execute(event_data):
                    event_data.result = True
                    break
        except Exception as err:
            event_data.error = err
            raise
        finally:
            await machine.callbacks(machine.finalize_event, event_data)
            _LOGGER.debug("%sExecuted machine finalize callbacks", machine.name)
        return event_data.result


class AsyncMachine(Machine):
    """ Machine manages states, transitions and models. In case it is initialized without a specific model
    (or specifically no model), it will also act as a model itself. Machine takes also care of decorating
    models with conveniences functions related to added transitions and states during runtime.

    Attributes:
        states (OrderedDict): Collection of all registered states.
        events (dict): Collection of transitions ordered by trigger/event.
        models (list): List of models attached to the machine.
        initial (str): Name of the initial state for new models.
        prepare_event (list): Callbacks executed when an event is triggered.
        before_state_change (list): Callbacks executed after condition checks but before transition is conducted.
            Callbacks will be executed BEFORE the custom callbacks assigned to the transition.
        after_state_change (list): Callbacks executed after the transition has been conducted.
            Callbacks will be executed AFTER the custom callbacks assigned to the transition.
        finalize_event (list): Callbacks will be executed after all transitions callbacks have been executed.
            Callbacks mentioned here will also be called if a transition or condition check raised an error.
        queued (bool): Whether transitions in callbacks should be executed immediately (False) or sequentially.
        send_event (bool): When True, any arguments passed to trigger methods will be wrapped in an EventData
            object, allowing indirect and encapsulated access to data. When False, all positional and keyword
            arguments will be passed directly to all callback methods.
        auto_transitions (bool):  When True (default), every state will automatically have an associated
            to_{state}() convenience trigger in the base model.
        ignore_invalid_triggers (bool): When True, any calls to trigger methods that are not valid for the
            present state (e.g., calling an a_to_b() trigger when the current state is c) will be silently
            ignored rather than raising an invalid transition exception.
        name (str): Name of the ``Machine`` instance mainly used for easier log message distinction.
    """

    state_cls = AsyncState
    transition_cls = AsyncTransition
    event_cls = AsyncEvent
    async_tasks = {}
    current_context = contextvars.ContextVar('current_context', default=None)

    async def dispatch(self, trigger, *args, **kwargs):  # ToDo: not tested
        """ Trigger an event on all models assigned to the machine.
        Args:
            trigger (str): Event name
            *args (list): List of arguments passed to the event trigger
            **kwargs (dict): Dictionary of keyword arguments passed to the event trigger
        Returns:
            bool The truth value of all triggers combined with AND
        """
        results = await self.await_all([partial(getattr(model, trigger), *args, **kwargs) for model in self.models])
        return all(results)

    async def callbacks(self, funcs, event_data):
        """ Triggers a list of callbacks """
        await self.await_all([partial(event_data.machine.callback, func, event_data) for func in funcs])

    async def callback(self, func, event_data):
        """ Trigger a callback function with passed event_data parameters. In case func is a string,
            the callable will be resolved from the passed model in event_data. This function is not intended to
            be called directly but through state and transition callback definitions.
        Args:
            func (string, callable): The callback function.
                1. First, if the func is callable, just call it
                2. Second, we try to import string assuming it is a path to a func
                3. Fallback to a model attribute
            event_data (EventData): An EventData instance to pass to the
                callback (if event sending is enabled) or to extract arguments
                from (if event sending is disabled).
        """
        func = self.resolve_callable(func, event_data)
        res = func(event_data) if self.send_event else func(*event_data.args, **event_data.kwargs)
        if inspect.isawaitable(res):
            await res

    @staticmethod
    async def await_all(callables):
        """
        Executes callables without parameters in parallel and collects their results.
        Args:
            partials (list): A list of callable functions

        Returns:
            list: A list of results. Using asyncio the list will be in the same order as the passed callables.
        """
        return await asyncio.gather(*[func() for func in callables])

    def switch_model_context(self, model):
        """
        This method is called by an `AsyncTransition` when all conditional tests have passed and the transition will happen.
        This requires already running tasks to be cancelled.
        Args:
            model (object): The currently processed model
        """
        running_task = self.async_tasks.get(model, None)
        if self.current_context.get() != running_task:
            if running_task is not None and running_task.done() is False:
                _LOGGER.debug("Cancel running tasks...")
                running_task.cancel()
            self.async_tasks[model] = self.current_context.get()

    async def process_context(self, func, model):
        """
        This function is called by an `AsyncEvent` to make callbacks processed in Event._trigger cancellable.
        Using asyncio this will result in a try-catch block catching CancelledEvents.
        Args:
            func (callable): The partial of Event._trigger with all parameters already assigned
            model (object): The currently processed model

        Returns:
            bool: returns the success state of the triggered event
        """
        if self.current_context.get() is None:
            self.current_context.set(asyncio.current_task())
            try:
                return await self._process(func)
            except asyncio.CancelledError:
                return False
        return await self._process(func)

    async def _process(self, trigger):
        # default processing
        if not self.has_queue:
            if not self._transition_queue:
                # if trigger raises an Error, it has to be handled by the Machine.process caller
                return await trigger()
            else:
                raise MachineError("Attempt to process events synchronously while transition queue is not empty!")

        self._transition_queue.append(trigger)
        # another entry in the queue implies a running transition; skip immediate execution
        if len(self._transition_queue) > 1:
            return True

        # execute as long as transition queue is not empty ToDo: not tested!
        while self._transition_queue:
            try:
                await self._transition_queue[0]()
                self._transition_queue.popleft()
            except Exception:
                # if a transition raises an exception, clear queue and delegate exception handling
                self._transition_queue.clear()
                raise
        return True


class HierarchicalAsyncMachine(HierarchicalMachine, AsyncMachine):

    state_cls = NestedAsyncState
    transition_cls = NestedAsyncTransition
    event_cls = NestedAsyncEvent

    async def trigger_event(self, _model, _trigger, *args, **kwargs):
        """ Processes events recursively and forwards arguments if suitable events are found.
        This function is usually bound to models with model and trigger arguments already
        resolved as a partial. Execution will halt when a nested transition has been executed
        successfully.
        Args:
            _model (object): targeted model
            _trigger (str): event name
            *args: positional parameters passed to the event and its callbacks
            **kwargs: keyword arguments passed to the event and its callbacks
        Returns:
            bool: whether a transition has been executed successfully
        Raises:
            MachineError: When no suitable transition could be found and ignore_invalid_trigger
                          is not True. Note that a transition which is not executed due to conditions
                          is still considered valid.
        """
        with self():
            res = await self._trigger_event(_model, _trigger, None, *args, **kwargs)
        return self._check_event_result(res, _model, _trigger)

    async def _trigger_event(self, _model, _trigger, _state_tree, *args, **kwargs):
        if _state_tree is None:
            _state_tree = self._build_state_tree(listify(getattr(_model, self.model_attribute)), self.state_cls.separator)
        res = {}
        for key, value in _state_tree.items():
            if value:
                with self(key):
                    res[key] = await self._trigger_event(_model, _trigger, value, *args, **kwargs)
            if not res.get(key, None) and _trigger in self.events:
                res[key] = await self.events[_trigger].trigger(_model, self, *args, **kwargs)
        return None if not res or all([v is None for v in res.values()]) else any(res.values())


class AsyncTimeout(AsyncState):
    """
    Adds timeout functionality to an asynchronous state. Timeouts are handled model-specific.

    Attributes:
        timeout (float): Seconds after which a timeout function should be
                         called.
        on_timeout (list): Functions to call when a timeout is triggered.
        runner (dict): Keeps track of running timeout tasks to cancel when a state is exited.
    """

    dynamic_methods = ["on_timeout"]

    def __init__(self, *args, **kwargs):
        """
        Args:
            **kwargs: If kwargs contain 'timeout', assign the float value to
                self.timeout. If timeout is set, 'on_timeout' needs to be
                passed with kwargs as well or an AttributeError will be thrown
                if timeout is not passed or equal 0.
        """
        self.timeout = kwargs.pop("timeout", 0)
        self._on_timeout = None
        if self.timeout > 0:
            try:
                self.on_timeout = kwargs.pop("on_timeout")
            except KeyError:
                raise AttributeError("Timeout state requires 'on_timeout' when timeout is set.")
        else:
            self._on_timeout = kwargs.pop("on_timeout", [])
        self.runner = {}
        super().__init__(*args, **kwargs)

    async def enter(self, event_data):
        """
        Extends `transitions.core.State.enter` by starting a timeout timer for
        the current model when the state is entered and self.timeout is larger
        than 0.

        Args:
            event_data (EventData): events representing the currently processed event.
        """
        if self.timeout > 0:
            self.runner[id(event_data.model)] = self.create_timer(event_data)
        await super().enter(event_data)

    async def exit(self, event_data):
        """
        Cancels running timeout tasks stored in `self.runner` first (when not note) before calling further exit callbacks.

        Args:
            event_data (EventData): Data representing the currently processed event.

        Returns:

        """
        timer_task = self.runner.get(id(event_data.model), None)
        if timer_task is not None:
            timer_task.cancel()
        await super().exit(event_data)

    def create_timer(self, event_data):
        """
        Creates and returns a running timer. Shields self._process_timeout to prevent cancellation when
        transitioning away from the current state (which cancels the timer) while processing timeout callbacks.
        Args:
            event_data (EventData): Data representing the currently processed event.

        Returns (cancellable): A running timer with a cancel method
        """
        async def _timeout():
            try:
                await asyncio.sleep(self.timeout)
                await asyncio.shield(self._process_timeout(event_data))
            except asyncio.CancelledError:
                pass

        return asyncio.ensure_future(_timeout())

    async def _process_timeout(self, event_data):
        _LOGGER.debug("%sTimeout state %s. Processing callbacks...", event_data.machine.name, self.name)
        await event_data.machine.callbacks(self.on_timeout, event_data)
        _LOGGER.info("%sTimeout state %s processed.", event_data.machine.name, self.name)
        self.runner[id(event_data.model)] = None

    @property
    def on_timeout(self):
        """
        List of strings and callables to be called when the state timeouts.
        """
        return self._on_timeout

    @on_timeout.setter
    def on_timeout(self, value):
        """ Listifies passed values and assigns them to on_timeout."""
        self._on_timeout = listify(value)
