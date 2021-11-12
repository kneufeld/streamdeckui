import logging
logger = logging.getLogger(__name__)

class DeviceMixin:
    """
    base class requires a weakref to a StreamDeck object
    """

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


class QuitKeyMixin:
    async def cb_keypress(self, pressed):
        await super().cb_keypress(pressed)

        # fire on key up not key down
        if not pressed:
            logger.info("you pushed the exit key")
            self.deck._quit_future.set_result(None)
