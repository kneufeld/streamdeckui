import io

from PIL import Image, ImageOps, ImageDraw, ImageFont
from StreamDeck.ImageHelpers import PILHelper

def resize_image(deck, key_spacing, image):
    """
    generates an image that is correctly sized to fit across all keys of
    a given deck.

    image: whatever Pillow.Image.open() can handle
    """
    from .deck import Deck

    if isinstance(deck, Deck):
        deck = deck._deck

    # TODO handle subset of deck keys
    key_rows, key_cols = deck.key_layout()
    key_width, key_height = deck.key_image_format()['size']

    # Compute total size of the full StreamDeck image, based on the number of
    # buttons along each axis. This doesn't take into account the spaces between
    # the buttons that are hidden by the bezel.
    key_width *= key_cols
    key_height *= key_rows

    # Compute the total number of extra non-visible pixels that are obscured by
    # the bezel of the StreamDeck.
    spacing_x, spacing_y = key_spacing
    spacing_x *= key_cols - 1
    spacing_y *= key_rows - 1

    # Compute final full deck image size, based on the number of buttons and
    # obscured pixels.
    full_deck_image_size = (key_width + spacing_x, key_height + spacing_y)

    # Resize the image to suit the StreamDeck's full image size. We use the
    # helper function in Pillow's ImageOps module so that the image's aspect
    # ratio is preserved.
    image = Image.open(image).convert("RGB")
    image = ImageOps.fit(image, full_deck_image_size, Image.LANCZOS)
    return image


# Crops out a key-sized image from a larger deck-sized image, at the location
# occupied by the given key index.
def crop_image(deck, image, key_spacing, key):
    key_rows, key_cols = deck.key_layout()
    key_width, key_height = deck.key_image_format()['size']
    spacing_x, spacing_y = key_spacing

    # Determine which row and column the requested key is located on.
    row = key // key_cols
    col = key % key_cols

    # Compute the starting X and Y offsets into the full size image that the
    # requested key should display.
    start_x = col * (key_width + spacing_x)
    start_y = row * (key_height + spacing_y)

    # Compute the region of the larger deck image that is occupied by the given
    # key, and crop out that segment of the full image.
    region = (start_x, start_y, start_x + key_width, start_y + key_height)
    segment = image.crop(region)

    # Create a new key-sized image, and paste in the cropped section of the
    # larger image.
    key_image = PILHelper.create_image(deck)
    key_image.paste(segment)

    return PILHelper.to_native_format(deck, key_image)

# Generates a custom tile with run-time generated text and custom image via the
# PIL module.
def render_key_image(deck, image):
    # Resize the source image asset to best-fit the dimensions of a single key,
    # leaving a margin at the bottom so that we can draw the key title
    # afterwards.

    if image is None:
        return black_image(deck)

    if isinstance(image, memoryview):
        return image

    image = Image.open(image)
    image = PILHelper.create_scaled_image(deck._deck, image, margins=[5, ] * 4)
    return PILHelper.to_native_format(deck._deck, image)

def add_text(deck, image, text, font=None, color='white'):

    if not text:
        return PILHelper.to_native_format(deck._deck, image)

    # covert BytesIO.getbuffer() back into something PIL can use
    if isinstance(image, memoryview):
        image = io.BytesIO(image)
        image = Image.open(image)

    if font is None:
        font = 'assets/Roboto-Regular.ttf'

    font = ImageFont.truetype(font, 14)

    draw = ImageDraw.Draw(image)
    draw.text(
        (image.width / 2, image.height - 5),
        text=text, font=font,
        anchor="ms", fill=color
    )

    return PILHelper.to_native_format(deck._deck, image)

def black_image(deck):
    image = PILHelper.create_image(deck._deck, 'black')
    return PILHelper.to_native_format(deck._deck, image)
