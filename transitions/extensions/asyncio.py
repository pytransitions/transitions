from ..core import Condition, Machine, Transition

import logging
import asyncio

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


class AsyncCondition(Condition):

    async def check(self, event_data):
        predicate = event_data.machine.resolve_callable(self.func, event_data)
        if asyncio.iscoroutinefunction(predicate):
            if event_data.machine.send_event:
                return await predicate(event_data) == self.target
            else:
                return await predicate(*event_data.args, **event_data.kwargs) == self.target
        else:
            print("SIMPLE RETURN")
            return super(AsyncCondition, self).check(event_data)


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


class AsyncMachine(Machine):

    transition_cls = AsyncTransition

    def callbacks(self, funcs, event_data):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            asyncio.gather(*[
                event_data.machine.callback(func, event_data) for func in funcs
            ])
        )

    async def callback(self, func, event_data):
        func = self.resolve_callable(func, event_data)

        if self.send_event:
            if asyncio.iscoroutinefunction(func):
                await func(event_data)
            else:
                func(event_data)
        else:
            if asyncio.iscoroutinefunction(func):
                await func(*event_data.args, **event_data.kwargs)
            else:
                func(*event_data.args, **event_data.kwargs)
