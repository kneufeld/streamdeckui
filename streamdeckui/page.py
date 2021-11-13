import weakref

from .utils import resize_image
from .key import Key

import logging
logger = logging.getLogger(__name__)

class Page:

    def __init__(self, deck, keys):
        self._deck = weakref.ref(deck) # deck ui object
        self._keys = []

        if keys is None:
            self._keys = [
                Key(self)
                for i in range(self.device.key_count())
            ]
        else:
            self._keys = keys

    def __str__(self):
        return self.__class__.__name__

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
        # HACK during Key.__init__ we often reference its index which calls this.
        # since the key hasn't been added to self.keys we call_soon() but
        # by then the key may have been deleted/swapped/etc.
        # tl;dr catch the value error and return -1. yuck.
        try:
            return self.keys.index(key)
        except ValueError:
            return -1

    def repaint(self):
        for key in self.keys:
            key.show_image(key.state)

    def background(self, image):
        """
        load and resize a source image so that it will fill the given deck
        """
        deck_image = resize_image(self.deck, self.deck.key_spacing, image)

        logger.debug(f"created deck image size of {deck_image.width}x{deck_image.height}")

        for key in self.keys:
            kimage = key.crop_image(deck_image)
            key.set_image(Key.UP, kimage)
