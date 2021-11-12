import asyncio
import weakref

from StreamDeck.ImageHelpers import PILHelper
from PIL import Image, ImageOps, ImageDraw, ImageFont
import aiohttp

from .reify import reify
from .utils import crop_image, render_key_image, add_text, black_image
from .mixins import DeviceMixin, QuitKeyMixin

import logging
logger = logging.getLogger(__name__)


from enum import IntEnum
class KeyState(IntEnum):
    UP = 0
    DOWN = 1
    DEFAULT = 2


class Key(DeviceMixin):
    def __init__(self, deck, index):
        self._deck = weakref.ref(deck) # deck ui object
        self._index = index
        self._images = {}

        # default image when key is pressed

        self.set_image(KeyState.UP, black_image(self.deck))
        self.set_image(KeyState.DOWN, 'assets/pressed.png')

    def __str__(self):
        return f"Key<{self._index}>"

    def add_label(self, state, text):
        image = self._images[state]
        image = add_text(self.deck, image, text)
        self.set_image(state, image)

    def set_image(self, state, image):
        """
        image should be a str or a cropped deck image
        """
        image = render_key_image(self.deck, image)
        self._images[state] = image

    def show_image(self, state):
        with self.deck:
            image = self._images[state]
            self.device.set_key_image(self._index, image)

    def crop_image(self, image):
        """
        image has already been processed by resize_image()
        return "our" section of the image
        """
        return crop_image(self.device, image, self.deck.key_spacing, self._index)

    async def cb_keypress(self, pressed):
        """
        pressed is True when key is pressed, hence False when released
        """
        logger.debug(f"{self}: {pressed}")

        state = KeyState.DOWN if pressed else KeyState.UP
        if state in self._images:
            self.show_image(state)


class NumberKey(QuitKeyMixin, Key):
    """
    dev page, show key index as text
    any key exits
    """

    def __init__(self, deck, index):
        super().__init__(deck, index)

        image = render_key_image(self.deck, None)
        image = add_text(self.deck, image, str(self._index), None)
        self.set_image(KeyState.UP, image)
        self.show_image(KeyState.UP)


class QuitKey(QuitKeyMixin, Key):
    pass


class UrlKey(Key):

    def __init__(self, deck, index, url, **kw):
        super().__init__(deck, index)
        self._url = url

    async def cb_keypress(self, pressed):
        if not pressed:
            return

        self.set_image(KeyState.DOWN, 'assets/safari-icon.png')
        self.show_image(KeyState.DOWN)

        self.set_image('error', 'assets/error.png')

        resp = await self.fetch(self._url)
        logger.info(f"GET: {self._url}: {resp.status}")

        if 200 >= resp.status <= 299:
            self.show_image(KeyState.UP)
        else:
            self.show_image('error')

    async def fetch(self, url):
        # https://docs.aiohttp.org/en/stable/client_reference.html
        async with aiohttp.ClientSession() as client:
            return await client.get(url)


class SwitchKey(Key):

    def __init__(self, deck, index, page, **kw):
        super().__init__(deck, index)
        self._page = page

    async def cb_keypress(self, pressed):
        if not pressed:
            return

        self.deck.change_page(self._page)
