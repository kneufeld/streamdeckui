import asyncio
import weakref

from StreamDeck.ImageHelpers import PILHelper

from .reify import reify
from .utils import resize_image, solid_image
from .key import Key
from .key import QuitKey, NumberKey, UrlKey, SwitchKey, BackKey
from .utils import crop_image, render_key_image, add_text

import logging
logger = logging.getLogger(__name__)

class Page(DeviceMixin):

    def __init__(self, deck, keys):
        self._deck = weakref.ref(deck) # deck ui object

        if keys is None:
            self._keys = [
                Key(self)
                for i in range(self.device.key_count())
            ]
        else:
            self._keys = keys

    @property
    def deck(self):
        return self._deck()

    @property
    def device(self):
        return self.deck._deck

    @property
    def keys(self):
        return self._keys

    def key_index(self, key):
        # HACK during Key creation we often reference its index which calls this.
        # since the key hasn't been added to self.keys it call_soon() but
        # by then the key may have been deleted/swapped/etc. tl;dr catch
        # the value error and return -1. yuck.
        try:
            return self.keys.index(key)
        except ValueError:
            return -1

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
            key.set_image(Key.UP, kimage)


class GreatWavePage(Page):
    def __init__(self, deck, keys):
        super().__init__(deck, keys)

        self._keys[-1] = QuitKey(self)
        # 'https://www2.burgundywall.com/beast/'
        self._keys[-2] = UrlKey(
            self, "http://localhost:8080/",
        )
        self._keys[0] = SwitchKey(self, 'numbers')
        self._keys[10] = BackKey(self)

        self.background('assets/greatwave.jpg')


class NumberedPage(Page):
    """
    a dev page that shows the index number of each key
    """
    def __init__(self, deck, keys):
        super().__init__(deck, keys)

        self._keys = [
            NumberKey(self)
            for i in range(self.device.key_count())
        ]

        self._keys[0] = SwitchKey(self, 'greatwave')
        self._keys[0].add_label(Key.UP, '0')

        self._keys[1] = SwitchKey(self, 'errorpage')
        self._keys[1].add_label(Key.UP, '1')

        self._keys[10] = BackKey(self)
        self._keys[10].add_label(Key.UP, '10')

        self._keys[-1] = QuitKey(self)
        self._keys[-1].add_label(Key.UP, '14')


class ErrorPage(Page):
    """
    assuming a 3x5 grid deck and we're passed all keys
    """

    def __init__(self, deck, keys):
        super().__init__(deck, keys)

        x = [1, 3, 7, 11, 13]
        red_image = solid_image(self.deck, 'red')

        for i in x:
            key = self._keys[i]
            key.set_image(Key.UP, red_image)

        self._keys[0] = SwitchKey(self, 'greatwave')
        self._keys[-1] = QuitKey(self)
        self._keys[10] = BackKey(self)
