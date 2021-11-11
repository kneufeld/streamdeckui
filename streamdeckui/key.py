import weakref

from .utils import crop_image, render_key_image

import logging
logger = logging.getLogger(__name__)

from enum import IntEnum
class KeyState(IntEnum):
    UP = 0
    DOWN = 1
    DEFAULT = 2

class Key:
    def __init__(self, deck, index):
        self._deck = weakref.ref(deck) # deck ui object
        self._index = index
        self._images = {}

    def __str__(self):
        return f"Key<{self._index}>"

    @property
    def deck(self):
        """
        get strong reference to deck ui object
        """
        return self._deck()

    @property
    def device(self):
        """
        deck hardware device
        """
        return self.deck._deck

    def set_image(self, state, image):
        # HACK
        if state == KeyState.DOWN:
            image = render_key_image(self.device, image, None, None)
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

        # fire on key up not key down
        if self._index == 14 and not pressed:
            logger.info("you pushed the exit key")
            self.deck._quit_future.set_result(None)
