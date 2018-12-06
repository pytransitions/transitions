from ..core import Condition, Machine, Transition

import logging
import asyncio
import itertools

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


class AsyncCondition(Condition):

    async def check(self, event_data):
        predicate = event_data.machine.resolve_callable(self.func, event_data)
        if event_data.machine.send_event:
            return await predicate(event_data) == self.target
        return await predicate(*event_data.args, **event_data.kwargs) == self.target


class AsyncTransition(Transition):

    condition_cls = AsyncCondition

    def _eval_conditions(self, event_data):
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(
            asyncio.gather(*[
                cond.check(event_data) for cond in self.conditions
            ])
        )
        if not all(res):
            _LOGGER.debug("%sTransition condition failed: Transition halted.", event_data.machine.name)
            return False
        return True

    def _prepare_state_change(self, event_data):
        _LOGGER.debug("Executed callback before conditions.")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            asyncio.gather(*[
                event_data.machine.callback(func, event_data) for func in self.prepare
            ])
        )

    def _before_state_change(self, event_data):
        _LOGGER.debug("Executed callback before transition.")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            asyncio.gather(*[
                event_data.machine.callback(func, event_data)
                    for func in itertools.chain(event_data.machine.before_state_change, self.before)
            ])
        )

    def _after_state_change(self, event_data):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            asyncio.gather(*[
                event_data.machine.callback(func, event_data)
                    for func in itertools.chain(self.after, event_data.machine.after_state_change)
            ])
        )
        _LOGGER.debug("Executed callback after transition.")


class AsyncMachine(Machine):

    transition_cls = AsyncTransition

    async def callback(self, func, event_data):
        func = asyncio.wrap_future(self.resolve_callable(func, event_data))
        if self.send_event:
            await func(event_data)
        else:
            await func(*event_data.args, **event_data.kwargs)