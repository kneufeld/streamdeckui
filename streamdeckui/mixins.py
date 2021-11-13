import logging
logger = logging.getLogger(__name__)

# these are mostly just example code and could easily be
# in your custom Key classes

class QuitKeyMixin:

    async def cb_key_up(self, *args, **kw):
        logger.info("you pushed the exit key")
        self.deck._quit_future.set_result(None)


class BackKeyMixin:

    async def cb_key_up(self, *args, **kw):
        from .key import Key

        self.state = Key.UP
        self.deck.prev_page()
