import logging
logger = logging.getLogger(__name__)


class QuitKeyMixin:

    async def cb_key_up(self, *args, **kw):
        logger.info("you pushed the exit key")
        self.deck._quit_future.set_result(None)
