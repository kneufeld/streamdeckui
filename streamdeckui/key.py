import asyncio
import weakref

from StreamDeck.ImageHelpers import PILHelper
from PIL import Image, ImageOps, ImageDraw, ImageFont
import aiohttp
import aiohttp.web

from .reify import reify
from .utils import crop_image, render_key_image, add_text, black_image
from .mixins import DeviceMixin, QuitKeyMixin

import logging
logger = logging.getLogger(__name__)


class Key(DeviceMixin):
    UP = 0
    DOWN = 1

    def __init__(self, page):
        self._page = weakref.ref(page)
        self._images = {}

        # default image when key is pressed

        self.set_image(Key.UP, black_image(self.deck))
        self.set_image(Key.DOWN, 'assets/pressed.png')

    def __str__(self):
        return f"Key<{self.index}>"

    @property
    def page(self):
        return self._page()

    @property
    def deck(self):
        return self.page.deck

    @property
    def device(self):
        return self.page.deck._deck

    @property
    def index(self):
        return self.page.key_index(self)

    def add_label(self, state, text, show=False):
        logger.debug("adding label: %s", text)
        image = self._images[state]
        image = add_text(self.deck, image, text)
        self.set_image(state, image)

        if show:
            self.show_image(state)

    def set_image(self, state, image):
        """
        image should be a str or a cropped deck image
        """
        image = render_key_image(self.deck, image)
        self._images[state] = image

    def show_image(self, state):
        with self.deck:
            image = self._images[state]
            self.device.set_key_image(self.index, image)

    def crop_image(self, image):
        """
        image has already been processed by resize_image()
        return "our" section of the image
        """
        return crop_image(self.device, image, self.deck.key_spacing, self.index)

    async def cb_keypress(self, pressed):
        """
        pressed is True when key is pressed, hence False when released
        """
        logger.debug(f"{self}: {pressed}")

        state = Key.DOWN if pressed else Key.UP
        if state in self._images:
            self.show_image(state)


class NumberKey(Key):
    """
    dev page, show key index as text
    any key exits
    """

    def __init__(self, page):
        super().__init__(page)

        # can't call self.index until after it's been added to page
        self.deck._loop.call_soon(self._add_label)

    def _add_label(self):
        if self.index < 0:
            return

        self.add_label(Key.UP, str(self.index), True)


class QuitKey(QuitKeyMixin, Key):
    pass


class UrlKey(Key):

    def __init__(self, page, url, **kw):
        super().__init__(page)
        self._url = url

    async def cb_keypress(self, pressed):
        if not pressed:
            return

        self.set_image(Key.DOWN, 'assets/safari-icon.png')
        self.show_image(Key.DOWN)

        self.set_image('error', 'assets/error.png')

        logger.debug("GET: %s", self._url)
        resp = await self.fetch(self._url)

        logger.info(f"GET: {self._url}: {resp.status}")

        if 200 >= resp.status <= 299:
            self.show_image(Key.UP)
        else:
            self.show_image('error')

    async def fetch(self, url):
        # https://docs.aiohttp.org/en/stable/client_reference.html
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as client:
            try:
                return await client.get(url)
            except Exception as e:
                logger.error(e)
                return aiohttp.web.Response(status=499)


class BackKey(Key):

    async def cb_keypress(self, pressed):
        if not pressed:
            return

        self.deck.prev_page()


class SwitchKey(Key):

    def __init__(self, page, to_page, **kw):
        super().__init__(page)
        self._to_page = to_page

    async def cb_keypress(self, pressed):
        if not pressed:
            return

        self.deck.change_page(self._to_page)
