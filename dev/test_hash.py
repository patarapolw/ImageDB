from PIL import Image
import imagehash


if __name__ == '__main__':
    im1 = Image.open('../user/images/blob/0a60e34f.png')
    w, h = im1.size

    for shift in range(0, 50, 10):
        im2 = Image.new('RGBA', (w+shift, h))
        im2.paste(im1, (shift, 0))

        print(imagehash.dhash(im1) - imagehash.dhash(im2))
