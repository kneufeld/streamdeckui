import asyncio
import weakref

from StreamDeck.ImageHelpers import PILHelper
from PIL import Image, ImageOps, ImageDraw, ImageFont
import aiohttp
import aiohttp.web

from .reify import reify
from .utils import crop_image, render_key_image, add_text, solid_image
from .mixins import QuitKeyMixin

import logging
logger = logging.getLogger(__name__)


class Key:
    UP = 0
    DOWN = 1

    def __init__(self, page):
        self._page = weakref.ref(page)
        self._images = {}
        self._state = Key.UP

        # default image when key is pressed
        self.set_image(Key.UP, solid_image(self.deck))
        self.set_image(Key.DOWN, 'assets/pressed.png')

        self.connect(True, True)

    def __str__(self):
        return f"Key<{self.index}>"

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value
        self.show_image(value)

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
        # NOTE weird stuff happens if you try to reify this
        return self.page.key_index(self)

    def connect(self, up, down):
        """
        connect to keypress signals
        """
        if up:
            self.deck.key_up.connect(self.key_up, sender=self)
        else:
            self.deck.key_up.disconnect(self.key_up, sender=self)

        if down:
            self.deck.key_down.connect(self.key_down, sender=self)
        else:
            self.deck.key_down.disconnect(self.key_down, sender=self)

    async def key_up(self, *args, **kw):
        self.state = Key.UP

    async def key_down(self, *args, **kw):
        self.state = Key.DOWN

    def add_label(self, state, text, show=False):
        # logger.debug("adding label: %s", text)
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
        self.set_image('fetch', 'assets/safari-icon.png')
        self.set_image('error', 'assets/error.png')

    async def key_up(self, *args, **kw):
        resp = await self.fetch(self._url)
        logger.info(f"GET: {self._url}: {resp.status}")

        if 200 >= resp.status <= 299:
            self.state = Key.UP
        else:
            self.state = 'error'

    async def fetch(self, url):
        logger.debug("GETing: %s", self._url)
        self.state = 'fetch'

        # https://docs.aiohttp.org/en/stable/client_reference.html
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as client:
            try:
                return await client.get(url)
            except Exception as e:
                logger.error(e)
                return aiohttp.web.Response(status=499)


class BackKey(Key):

    def __init__(self, page, **kw):
        super().__init__(page)
        self.set_image(Key.UP, 'assets/back.png')

    async def key_up(self, *args, **kw):
        self.state = Key.UP
        self.deck.prev_page()


class SwitchKey(Key):

    def __init__(self, page, to_page, **kw):
        super().__init__(page)
        self._to_page = to_page

    async def key_up(self, *args, **kw):
        self.state = Key.UP
        self.deck.change_page(self._to_page)
