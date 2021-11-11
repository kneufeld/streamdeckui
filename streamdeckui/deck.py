import asyncio

from .key import Key, KeyState
from .utils import resize_image
from .reify import reify

import logging
logger = logging.getLogger(__name__)

class Deck:
    key_spacing = (36, 36)

    def __init__(self, deck, keys=None, clear=True, loop=None):
        self._loop = loop or asyncio.get_event_loop()
        self._quit_future = asyncio.Future(loop=loop)

        self._deck = deck
        self._brightness = .4
        self._clear = clear

        if keys is None:
            self._keys = [Key(self, i) for i in range(self._deck.key_count())]
        else:
            self._keys = keys

        self._deck.reset()

        self._deck.set_key_callback_async(self.cb_keypress)
        # callback = functools.partial(key_change_callback, quit_future)
        # deck.set_key_callback_async(callback, quit_future.get_loop())

    @reify
    def serial_number(self):
        return self._deck.get_serial_number()

    def __str__(self):
        return self.serial_number

    def release(self):
        if self._clear:
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

    def background(self, image):
        """
        load and resize a source image so that it will fill the given deck
        """
        deck_image = resize_image(self._deck, Deck.key_spacing, image)

        logger.debug(f"created deck image size of {deck_image.width}x{deck_image.height}")

        for key in self:
            kimage = key.crop_image(deck_image)
            key.set_image(KeyState.UP, kimage)
            key.show_image(KeyState.UP)

    @property
    def keys(self):
        return self._keys

    def __iter__(self):
        """
        for key in deck: pass
        """
        return iter(self.keys)

    async def cb_keypress(self, _, key, state):
        await self._keys[key].cb_keypress(state)

    async def wait(self):
        await self._quit_future
