from imagedb import ImageDB
from PIL import Image
import imagehash


if __name__ == '__main__':
    db = ImageDB('../user/images.db')
    hashes = dict()
    for db_image in db.search():
        if not db_image.image_hash:
            im = Image.open(db_image.path)
            h = str(imagehash.dhash(im))
            db_image.image_hash = h
            print(db_image.image_hash)
            # db.session.commit()
            # print(db_image.to_json())
