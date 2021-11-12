import logging
logger = logging.getLogger(__name__)


class QuitKeyMixin:
    async def cb_keypress(self, pressed):
        await super().cb_keypress(pressed)

        # fire on key up not key down
        if not pressed:
            logger.info("you pushed the exit key")
            self.deck._quit_future.set_result(None)
