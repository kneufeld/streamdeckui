# Stream Deck UI Framework notes

To make programming and using the stream deck easier some ui framework
appears to be in order.

## Objects

key: a button
page: a collection of keys
deck: the deck itself but with some ui helper functions

### Key

I'd have called them buttons but I'll follow the original authors lead here.

* list of _callbacks_ on _key up_, _key down_, _both_.
* image list for [on_load, key down, key up]
* thread function: if specified, run the function in a thread. required for animated buttons.
* maybe have concept of background image and transparent key images?
* set text, fonts?

### Page

A collection of keys.

* background image
* maybe have subset of keys instead of all of them
