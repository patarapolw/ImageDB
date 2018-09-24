from threading import Thread
from time import sleep
import webbrowser
from PIL import Image, ImageChops
import enum
from pathlib import Path
import imagehash
from send2trash import send2trash


def open_browser_tab(url):
    def _open_tab():
        sleep(1)
        webbrowser.open_new_tab(url)

    thread = Thread(target=_open_tab)
    thread.daemon = True
    thread.start()


def trim_image(im):
    bg = Image.new(im.mode, im.size, im.getpixel((0,0)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()

    if bbox:
        im = im.crop(bbox)

    return im


def shrink_image(im, max_width=800):
    width, height = im.size

    if width > max_width:
        im.thumbnail((max_width, height * max_width / width))

    return im


def remove_duplicate(file_path):
    hashes = set()

    for p in Path(file_path).glob('**/*.*'):
        if p.suffix.lower() in {'.png', '.jpg', '.jp2', '.jpeg', '.gif'}:
            h = imagehash.dhash(trim_image(shrink_image(Image.open(p))))
            if h in hashes:
                print('Deleting {}'.format(p))
                send2trash(p)
            else:
                hashes.add(h)


class HAlign(enum.Enum):
    LEFT = -1
    CENTER = 0
    RIGHT = 1


class VAlign(enum.Enum):
    TOP = 1
    MIDDLE = 0
    BOTTOM = -1

