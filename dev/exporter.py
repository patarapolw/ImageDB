from imagedb import ImageDB
from PIL import Image
import imagehash


if __name__ == '__main__':
    db = ImageDB('../user/images.db')
    hashes = dict()
    for image in db.search():
        im = Image.open(image.path)
        h = str(imagehash.dhash(im))
        hashes.setdefault(h, []).append(image.path)

    diff = dict()
    hash_list = list(hashes.keys())
    for i in range(len(hash_list)-1):
        for j in range(i+1, len(hash_list)):
            d0 = imagehash.hex_to_hash(hash_list[i])\
                 - imagehash.hex_to_hash(hash_list[j])
            diff[(i, j)] = d0

    diff = sorted(diff, key=lambda x: x[1])
    i, j = diff[0]
    print(hashes[hash_list[i]])
    print(hashes[hash_list[j]])
    print()

    i, j = diff[-1]
    print(hashes[hash_list[i]])
    print(hashes[hash_list[j]])
    print()
