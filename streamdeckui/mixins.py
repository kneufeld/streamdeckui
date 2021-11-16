import os
import signal
import asyncio

import logging
logger = logging.getLogger(__name__)

# these are mostly just example code and could easily be
# in your custom Key classes

class QuitKeyMixin:
    """
    choose how to stop listening for streamdeck events

    pass in a Future and we'll set a result on it:
    key = QuitKey(exit_method=deck._quit_future)
    await deck.run()

    or if future is None then send a SIGTERM to ourselves. This is a bit
    more involved but allows multiple "things" to cause an exit

    def handle_term(signum, frame):
        raise SystemExit()

    signal.signal(signal.SIGTERM, handle_term)

    try:
       # create Deck, etc
       key = QuitKey(exit_method='sigterm')
       loop.run_forever()
    except SystemExit:
        loop.run_until_complete(deck.release())
    """

    def __init__(self, *args, exit_method='sigterm', **kw):
        """
        exit_method can be 'sigterm' or a Future() object
        """
        super().__init__(*args, **kw)
        self._exit_method = exit_method

    async def cb_key_up(self, *args, **kw):
        logger.info("you pushed the exit key")

        if self._exit_method == 'sigterm':
            os.kill(os.getpid(), signal.SIGTERM)

        elif isinstance(self._exit_method, asyncio.Future):
            self._future.set_result(None)

        else:
            raise RuntimeError(f"unknown exit method: {self._exit_method}")


class BackKeyMixin:

    async def cb_key_up(self, *args, **kw):
        from .key import Key

        self.state = Key.UP
        self.deck.prev_page()
