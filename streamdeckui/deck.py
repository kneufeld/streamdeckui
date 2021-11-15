import asyncio

import blinker

from .reify import reify
from .periodic import Periodic
from .timers import Timers

import logging
logger = logging.getLogger(__name__)


class Deck:
    key_spacing = (36, 36)

    def __init__(self, deck, keys=None, clear=True, loop=None, **kw):
        self._loop = loop or asyncio.get_event_loop()

        self._quit_future = asyncio.Future(loop=loop)
        # self._quit_future.add_done_callback(self.release)

        self._deck = deck
        self._brightness = .4
        self._clear = clear

        self._futures = []

        self.key_up = blinker.signal('key_up')
        self.key_down = blinker.signal('key_down')

        self._pages = {}
        self._page_history = [] # track page navigation on a stack

        self._deck.reset()
        self._deck.set_key_callback(self.cb_keypress)

        self._timers = Timers(self, loop, **kw)

    @reify
    def serial_number(self):
        return self._deck.get_serial_number()

    def __str__(self):
        return self.serial_number

    def release(self, *args):
        """
        call at least once on exiting, sometimes called twice
        depending on ctrl-c vs more graceful exit. Hence set
        _deck to None
        """
        if self._deck is None:
            return

        if self._clear:
            with self._deck:
                self.turn_off()
                self._deck.reset()

        with self._deck:
            self._deck.close()

        self._deck = None

    def __enter__(self):
        """
        get lock on self._deck
        """
        self._deck.update_lock.acquire()

    def __exit__(self, type, value, traceback):
        """
        Exit handler for the StreamDeck, releasing the exclusive update lock on
        the deck.
        """
        self._deck.update_lock.release()

    @property
    def brightness(self):
        return self._brightness

    @brightness.setter
    def brightness(self, value):
        with self._deck:
            self._brightness = value
            self._deck.set_brightness(value)

    def turn_on(self):
        # note that self._brightness is not changed
        with self._deck:
            self._deck.set_brightness(self._brightness)

    def turn_off(self):
        # note that self._brightness is not changed
        with self._deck:
            self._deck.set_brightness(0)

    @property
    def page(self):
        """
        active page
        """
        curr_page = self._page_history[-1]
        return self._pages[curr_page]

    def add_page(self, name, page):
        logger.debug("adding page: %s: %s", name, page)
        self._pages[name] = page

    def change_page(self, name):
        logger.debug("change to page: %s", name)
        self._page_history.append(name)
        self.page.repaint()

    def prev_page(self):
        """
        go to previous page, pop item off page history
        """
        if len(self._page_history) <= 1:
            return None

        self._page_history.pop()
        logger.debug("goto prev page: %s", self._page_history[-1])

        self.page.repaint()
        return self.page

    async def cb_keypress_async(self, device, key, pressed):
        # NOTE now we're in the main thread
        key = self.page.keys[key]

        if pressed:
            return self.key_down.send_async(key)
        else:
            return self.key_up.send_async(key)

    def cb_keypress(self, device, key, state):
        # NOTE we're in the streamdeck worker thread, not main
        fut = asyncio.run_coroutine_threadsafe(
            self.cb_keypress_async(device, key, state),
            self._loop
        )
        self._futures.append(fut)

    async def block_until_quit(self):
        """
        await on this method to "run forever" the program
        """
        # self._loop.create_task(self.check_futures())
        check_futures = Periodic(self._loop, 3, self.check_futures)
        check_futures.start()

        logger.debug("waiting for quit signal...")
        await self._quit_future
        await check_futures.stop()

    async def check_futures(self):
        """
        check every few seconds that the futures scheduled from the
        streamdeck worker thread haven't thrown an exception

        this isn't "required" to do but any problems in a key callback
        (basically anything we're trying to accomplish) just disappear
        into the void and makes debugging virtually impossible. Or log
        a stacktrace as required.
        """
        # logger.debug("check_futures: %s", self._futures)
        remove = []

        for fut in self._futures:
            if not fut.done():
                continue

            try:
                results = fut.result() # raises exception if applicable

                # not totally confident I know what's going on here...
                # I think blink-async:send_async() returns the receiver
                # callback and the results of the callback, which in our case
                # is the nested coroutine. I think... It seems to work though.
                for receiver_cb, task in results:
                    await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.exception(e)
            finally:
                remove.append(fut)

        for fut in remove:
            self._futures.remove(fut)
