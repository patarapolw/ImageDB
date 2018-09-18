from threading import Thread
from time import sleep
import webbrowser
from PIL import Image, ImageChops


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


def shrink_image(im, max_width=800, max_height=600):
    width, height = im.size

    if width / height < max_width / max_height:
        im.thumbnail((max_height, max_height))
    else:
        im.thumbnail((max_width, max_width))

    return im
