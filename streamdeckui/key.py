import asyncio
import weakref
import pathlib

from .utils import ASSET_PATH
from .utils import crop_image, render_key_image, add_text, solid_image

import logging
logger = logging.getLogger(__name__)

class Key:
    UP = 0
    DOWN = 1

    def __init__(self, page, **kw):
        self._page = weakref.ref(page)
        self._images = {}
        self._state = Key.UP

        up_image = kw.get('up_image', solid_image(self.deck))
        down_image = kw.get('down_image', ASSET_PATH / 'pressed.png')

        self.set_image(Key.UP, up_image)
        self.set_image(Key.DOWN, down_image)

        self.add_label(Key.UP, kw.get('label', ''))

        self.connect(
            kw.get('conn_up', True),
            kw.get('conn_down', True),
        )

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
            self.deck.key_up.connect(self.cb_key_up, sender=self)
        else:
            self.deck.key_up.disconnect(self.cb_key_up, sender=self)

        if down:
            self.deck.key_down.connect(self.cb_key_down, sender=self)
        else:
            self.deck.key_down.disconnect(self.cb_key_down, sender=self)

    async def cb_key_up(self, *args, **kw):
        self.state = Key.UP

    async def cb_key_down(self, *args, **kw):
        self.state = Key.DOWN

    def add_label(self, state, text, show=False):
        if not text:
            return

        # logger.debug("adding label: %s", text)
        image = self._images[state]
        image = add_text(self.deck, image, text)
        self.set_image(state, image)

        if show:
            self.show_image(state)

    def crop_image(self, image):
        """
        image has already been processed by resize_image()
        return "our" section of the image
        """
        return crop_image(self.device, image, self.deck.key_spacing, self.index)

    def set_image(self, state, image):
        """
        store the image but do not show it, use show_image for that
        """
        if isinstance(image, pathlib.PurePath):
            image = str(image)

        image = render_key_image(self.deck, image)
        self._images[state] = image

    def show_image(self, state):
        if self.index < 0:
            return

        with self.deck:
            image = self._images[state]
            self.device.set_key_image(self.index, image)
