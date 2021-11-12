import asyncio
from collections import defaultdict

import blinker

from .key import Key
from .utils import resize_image
from .reify import reify

import logging
logger = logging.getLogger(__name__)

class Deck:
    key_spacing = (36, 36)
    dim_timer = 10
    off_timer = 10 # set after dim_timer

    def __init__(self, deck, keys=None, clear=True, loop=None):
        self._loop = loop or asyncio.get_event_loop()
        self._dim_timer = None
        self._off_timer = None

        self._quit_future = asyncio.Future(loop=loop)
        self._quit_future.add_done_callback(self.release)

        self._deck = deck
        self._brightness = .4
        self._clear = clear

        self._futures = []

        self.key_up = blinker.signal('key_up')
        self.key_down = blinker.signal('key_down')

        # THINK TODO make a key "copy" function, currently it's tedious
        # to "change" a button type. Most of the time we just want
        # a different callback function, could that be a composable
        # object?

        self._pages = {}
        self._page_history = [] # track page navigation on a stack

        self._deck.reset()
        self._deck.set_key_callback_async(self.cb_keypress)

        # reset_timers turns on the screen but we don't want to do
        # that until all key images have been uploaded, otherwise
        # we see a flash of the default deck icon. This gets called
        # as soon as we wait on _quit_future
        self._loop.call_soon(self.reset_timers)

    @reify
    def serial_number(self):
        return self._deck.get_serial_number()

    def __str__(self):
        return self.serial_number

    def release(self, *args):
        if self._clear:
            with self._deck:
                self.turn_off()
                self._deck.reset()

        with self._deck:
            self._deck.close()

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
        self._brightness = value
        self._deck.set_brightness(value)

    def turn_on(self):
        # note that self._brightness is not changed
        self._deck.set_brightness(self._brightness)

    def turn_off(self):
        # note that self._brightness is not changed
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
        return self.page

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

    def background(self, image):
        """
        load and resize a source image so that it will fill the given deck
        """
        deck_image = resize_image(self._deck, Deck.key_spacing, image)

        logger.debug(f"created deck image size of {deck_image.width}x{deck_image.height}")

        for key in self.keys:
            kimage = key.crop_image(deck_image)
            key.set_image(Key.UP, kimage)
            key.show_image(Key.UP)

    @property
    def keys(self):
        return self.page.keys

    def __iter__(self):
        """
        for key in deck: pass
        """
        return iter(self.keys)

    async def cb_keypress_async(self, _, key, pressed):
        self.reset_timers()
        key = self.keys[key]

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

    async def cb_wakeup(self, _, key, state):
        # only fire on keyup otherwise this is called twice
        if state is False:
            self.reset_timers()
            self._deck.set_key_callback(self.cb_keypress)

    async def wait(self):
        await self._quit_future

    def reset_timers(self):
        """
        on each keypress the timers are reset
        when the dim timer fires the display is dimmed but keys work as expected
        when the dim timer fires it sets the off timer

        when the off timer fires it turns off the display and changes out
        the keypress call back to only turn back on the display and not
        fire the actual keypress event
        """
        self.turn_on()

        if self._dim_timer:
            self._dim_timer.cancel()

        if self._off_timer:
            self._off_timer.cancel()

        self._dim_timer = self._loop.call_later(Deck.dim_timer, self.cb_dim_timer)

    def cb_dim_timer(self):
        self._deck.set_brightness(self.brightness / 2)
        self._off_timer = self._loop.call_later(Deck.off_timer, self.cb_off_timer)

    def cb_off_timer(self):
        self.turn_off()
        self._deck.set_key_callback_async(self.cb_wakeup)
