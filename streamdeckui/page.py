import asyncio
import weakref

from StreamDeck.ImageHelpers import PILHelper

from .reify import reify
from .utils import resize_image, black_image
from .mixins import DeviceMixin
from .key import Key
from .key import QuitKey, NumberKey, UrlKey, SwitchKey, BackKey
from .utils import crop_image, render_key_image, add_text

import logging
logger = logging.getLogger(__name__)

class Page(DeviceMixin):

    def __init__(self, deck, keys):
        self._deck = weakref.ref(deck) # deck ui object
        self._keys = keys

    @property
    def keys(self):
        return self._keys

    def repaint(self):
        for key in self.keys:
            key.show_image(Key.UP)

    def background(self, image):
        """
        load and resize a source image so that it will fill the given deck
        """
        deck_image = resize_image(self.deck, self.deck.key_spacing, image)

        logger.debug(f"created deck image size of {deck_image.width}x{deck_image.height}")

        for key in self.keys:
            kimage = key.crop_image(deck_image)
            key.set_image(KeyState.UP, kimage)


class GreatWavePage(Page):
    def __init__(self, deck, keys):
        super().__init__(deck, keys)

        self._keys = [Key(self.deck, i) for i in range(self.device.key_count())]
        self._keys[-1] = QuitKey(self.deck, len(self._keys) - 1)
        self._keys[-2] = UrlKey(
            self.deck, len(self._keys) - 2,
            # 'https://www2.burgundywall.com/beast/'
            'http://localhost:8080/'
        )
        self.keys[0] = SwitchKey(self.deck, 0, 'numbers')

        self.background('assets/greatwave.jpg')


class NumberedPage(Page):
    """
    a dev page that shows the index number of each key
    """
    def __init__(self, deck, keys):
        super().__init__(deck, keys)

        self._keys = [
            NumberKey(self.deck, i)
            for i in range(self.device.key_count())
        ]

        self._keys[0] = SwitchKey(self.deck, 0, 'greatwave')
        self._keys[0].add_label(KeyState.UP, '0')


class ErrorPage(Page):
    """
    assuming a 3x5 grid deck and we're passed all keys
    """

    def __init__(self, deck, keys):
        super().__init__(deck, keys)


