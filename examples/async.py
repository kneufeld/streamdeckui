#!/usr/bin/env python3

import asyncio

from StreamDeck.DeviceManager import DeviceManager
from streamdeckui import Deck, Page, Key
from streamdeckui.mixins import QuitKeyMixin, BackKeyMixin
from streamdeckui.utils import ASSET_PATH

import logging
logger = logging.getLogger(__name__)


class QuitKey(QuitKeyMixin, Key):
    def __init__(self, page, **kw):
        super().__init__(page, **kw)
        self.set_image(Key.UP, ASSET_PATH / 'power.png')


class NumberedPage(Page):
    """
    a dev page that shows the index number of each key
    """
    def __init__(self, deck, keys):
        super().__init__(deck, [])

        self._keys = [
            Key(self, label=str(i))
            for i in range(self.device.key_count())
        ]

        self._keys[-1] = QuitKey(self, label='14')


async def main(deck):
    """
    deck is a streamdeckui.Deck

    A complete app can be found (eventually) at:
    https://github.com/kneufeld/helmdeck
    """

    deck.add_page('numbers', NumberedPage(deck, None))
    deck.change_page('numbers')

    deck.turn_on()

    await deck.block_until_quit()


if __name__ == "__main__":
    streamdeck = DeviceManager().enumerate()[0]
    streamdeck.open()

    try:
        loop = asyncio.get_event_loop()
        deck = Deck(streamdeck, clear=True, loop=loop) # convert to deck ui
        loop.run_until_complete(main(deck))
    except KeyboardInterrupt:
        logger.warning("ctrl-c quitting")
    finally:
        deck.release()
