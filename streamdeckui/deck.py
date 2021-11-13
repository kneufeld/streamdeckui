import asyncio
import weakref

import blinker

from .key import Key
from .utils import resize_image
from .reify import reify

import logging
logger = logging.getLogger(__name__)


class Timers:
    """
    this class holds all the timers related to screen brightness and
    any other timers required. Moved into its own class to simplify
    the Deck class
    """

    dim_time = 30
    off_time = 60 # set after dim_timer fires

    def __init__(self, deck, loop, **kw):
        self._deck = weakref.ref(deck)
        self._loop = loop

        self.dim_time = kw.get('dim_time', Timers.dim_time)
        self.off_time = kw.get('off_time', Timers.off_time)

        self._dim_timer = None
        self._off_timer = None

        self.deck.key_down.connect(self.cb_key_down)

        self.reset_timers()

    @property
    def deck(self):
        return self._deck()

    @property
    def device(self):
        return self.deck._deck

    def cb_key_down(self, key):
        self.deck.turn_on()         # restore potentially dimmed screen
        self.reset_timers()

    def cb_dim_timer(self):
        self.device.set_brightness(self.deck.brightness / 2)
        self._off_timer = self._loop.call_later(self.off_time, self.cb_off_timer)

    def cb_off_timer(self):
        self.deck.turn_off()
        self.device.set_key_callback_async(self.cb_wakeup)

    async def cb_wakeup(self, device, key, pressed):
        """
        user pushed a key after display was off, turn the deck
        back on and restore normal callbacks
        """
        # only restore callbaks on keyup otherwise the keyup event will
        # get caught in the standard callbacks which isn't what you want
        if pressed:
            # turn on during keydown
            self.deck.turn_on()
        else:
            # restore callbacks on keyup
            self.reset_timers()
            self.device.set_key_callback(self.deck.cb_keypress)

    def reset_timers(self):
        """
        on each keypress the timers are reset
        when the dim timer fires the display is dimmed but keys work as expected
        when the dim timer fires it sets the off timer

        when the off timer fires it turns off the display and changes out
        the keypress call back to only turn back on the display and not
        fire the actual keypress event
        """
        # NOTE it's tempting to call turn_on() here but there's a race
        # condition at startup where no pages have been created yet so you
        # get a flash of the default streamdeck icon

        if self._dim_timer:
            self._dim_timer.cancel()

        if self._off_timer:
            self._off_timer.cancel()

        self._dim_timer = self._loop.call_later(self.dim_time, self.cb_dim_timer)


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
            self.key_down.send_async(key)
        else:
            self.key_up.send_async(key)

    def cb_keypress(self, device, key, state):
        # NOTE we're in the streamdeck worker thread, not main
        fut = asyncio.run_coroutine_threadsafe(
            self.cb_keypress_async(device, key, state), self._loop
        )
        self._futures.append(fut)

    async def block_until_quit(self):
        """
        await on this method to "run forever" the program
        """
        self._loop.create_task(self.check_futures())
        await self._quit_future

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
                fut.result() # raises exception if applicable
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.exception(e)
            finally:
                remove.append(fut)

        for fut in remove:
            self._futures.remove(fut)

        loop = self._loop
        loop.call_later(3, loop.create_task, self.check_futures())
