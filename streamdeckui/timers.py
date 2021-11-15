import weakref

import blinker

import logging
logger = logging.getLogger(__name__)

class Timers:
    """
    this class holds all the timers related to screen brightness and
    any other timers required. Moved into its own class to simplify
    the Deck class
    """

    dim_time = 30
    off_time = 60 # set after dim_timer fires

    def __init__(self, deck, loop, **kw):
        self._deck = weakref.ref(deck)
        self._loop = loop

        self.dim_time = kw.get('dim_time', Timers.dim_time)
        self.off_time = kw.get('off_time', Timers.off_time)

        self._dim_timer = None
        self._off_timer = None

        self.deck.key_down.connect(self.cb_key_down)

        self.reset_timers()

    @property
    def deck(self):
        return self._deck()

    @property
    def device(self):
        return self.deck._deck

    def cb_key_down(self, key):
        self.deck.turn_on()         # restore potentially dimmed screen
        self.reset_timers()

    def cb_dim_timer(self):
        self.device.set_brightness(self.deck.brightness / 2)
        self._off_timer = self._loop.call_later(self.off_time, self.cb_off_timer)

    def cb_off_timer(self):
        self.deck.turn_off()
        self.device.set_key_callback_async(self.cb_wakeup)

    async def cb_wakeup(self, device, key, pressed):
        """
        user pushed a key after display was off, turn the deck
        back on and restore normal callbacks
        """
        # only restore callbaks on keyup otherwise the keyup event will
        # get caught in the standard callbacks which isn't what you want
        if pressed:
            # turn on during keydown
            self.deck.turn_on()
        else:
            # restore callbacks on keyup
            self.reset_timers()
            self.device.set_key_callback(self.deck.cb_keypress)

    def reset_timers(self):
        """
        on each keypress the timers are reset
        when the dim timer fires the display is dimmed but keys work as expected
        when the dim timer fires it sets the off timer

        when the off timer fires it turns off the display and changes out
        the keypress call back to only turn back on the display and not
        fire the actual keypress event
        """
        # NOTE it's tempting to call turn_on() here but there's a race
        # condition at startup where no pages have been created yet so you
        # get a flash of the default streamdeck icon

        if self._dim_timer:
            self._dim_timer.cancel()

        if self._off_timer:
            self._off_timer.cancel()

        self._dim_timer = self._loop.call_later(self.dim_time, self.cb_dim_timer)
