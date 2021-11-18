# from https://stackoverflow.com/questions/37512182/how-can-i-periodically-execute-a-function-with-asyncio

import asyncio
import inspect
from contextlib import suppress
from functools import partial
import itertools

import logging
logger = logging.getLogger(__name__)

def is_async(func):
    # python 3.8 changed how an async function is passed through a functools.partial
    # so "follow" any nested partials to get to the "real" function and test that
    while isinstance(func, partial):
        func = func.func

    return inspect.isawaitable(func) or \
        inspect.isasyncgenfunction(func) or \
        asyncio.iscoroutinefunction(func)

class Periodic:
    def __init__(self, loop, time, func, *func_args, **func_kwargs):
        self.time = time
        self.func = (func, func_args, func_kwargs)
        self.loop = loop or asyncio.get_event_loop()

        self.is_started = False
        self._task      = None

    def start(self):
        # logger.debug(f"{self.__class__.__name__}.start()")

        if not self.is_started:
            self.is_started = True
            # task to call func periodically
            self._task = self.loop.create_task(self._run())

    async def stop(self):
        # logger.debug(f"{self.__class__.__name__}.stop()")

        if self.is_started:
            self.is_started = False
            # stop task and await it stopped:
            with suppress(asyncio.CancelledError):
                self._task.cancel()
                await self._task

    async def _run(self):
        func, args, kwargs = self.func
        _is_async = is_async(func)

        while True:
            await asyncio.sleep(self.time)
            # logger.debug(f"{self.__class__.__name__} tick {self.time}")

            if _is_async:
                await func(*args, **kwargs)
            else:
                func(*args, **kwargs)


class Alternating(Periodic):
    def __init__(self, loop, time, funcs):
        """
        funcs: a list of functions that are continously cycled through
        """
        super().__init__(loop, time, self.cycle)
        self._next = itertools.cycle(funcs)

    async def cycle(self):
        cb = next(self._next)
        # logger.debug(f"{self.__class__.__name__}.cycle() {cb}")
        await cb()
