import os
from PIL import ImageGrab
from io import BytesIO
import re

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from . import db


class ImageDB:
    def __init__(self, db_path):
        self.engine = create_engine('sqlite:///' + db_path)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        if not os.path.exists(db_path):
            db.Base.metadata.create_all(self.engine)

    def from_clipboard(self, tag_or_tags=None):
        im = ImageGrab.grabclipboard()
        if im is not None:
            fp = BytesIO()
            im.save(fp, format='png')

            db_image = db.Image()
            db_image.data = fp.getvalue()

            self.session.add(db_image)
            self.session.commit()

            if tag_or_tags:
                self.mark(db_image, tag_or_tags)

            return db_image

    def mark(self, db_image, tag_or_tags='marked'):
        def _mark(tag):
            db_tag = self.session.query(db.Tag).filter_by(name=tag).first()
            if db_tag is None:
                db_tag = db.Tag()
                db_tag.name = tag

                self.session.add(db_tag)
                self.session.commit()

            db_tic = self.session.query(db.TagImageConnect).filter_by(tag_id=db_tag.id,
                                                                      image_id=db_image.id).first()
            if db_tic is None:
                db_tic = db.TagImageConnect()
                db_tic.tag_id = db_tag.id
                db_tic.card_id = db_tic.id

                self.session.add(db_tic)
                self.session.commit()
            else:
                pass
                # raise ValueError('The card is already marked by "{}".'.format(tag))

            return db_tag

        if isinstance(tag_or_tags, str):
            yield _mark(tag_or_tags)
        else:
            for x in tag_or_tags:
                yield _mark(x)

    def unmark(self, db_image, tag_or_tags='marked'):
        def _unmark(tag):
            db_tag = self.session.query(db.Tag).filter_by(name=tag).first()
            if db_tag is None:
                raise ValueError('Cannot unmark "{}"'.format(tag))
                # return

            db_tic = self.session.query(db.TagImageConnect).filter_by(tag_id=db_tag.id,
                                                                     card_id=db_image.id).first()
            if db_tic is None:
                raise ValueError('Cannot unmark "{}"'.format(tag))
                # return
            else:
                self.session.delete(db_tic)
                self.session.commit()

            yield db_tag

        if isinstance(tag_or_tags, str):
            yield _unmark(tag_or_tags)
        else:
            for x in tag_or_tags:
                yield _unmark(x)

    def search(self, content=None, tag_or_tags=None, type_='partial'):
        def _compare(text, text_compare):
            if type_ == 'partial':
                return text_compare in text
            elif type_ in {'regex', 'regexp', 're'}:
                return re.search(text_compare, text, flags=re.IGNORECASE)
            else:
                return text_compare == text

        def _filter_tag(text_compare):
            for db_image in query:
                if any(_compare(tic.tag.name, text_compare) for tic in db_image.tags):
                    yield db_image

        def _filter_slide(text_compare):
            for db_card in query:
                if any(_compare(db_image.info, text_compare) for db_image in query if db_image.info):
                    yield db_card

        query = iter(self.session.query(db.Image).order_by(db.Image.modified.desc()))

        if tag_or_tags:
            if isinstance(tag_or_tags, str):
                query = _filter_tag(tag_or_tags)
            else:
                for tag in tag_or_tags:
                    query = _filter_tag(tag)

        if content:
            query = _filter_slide(content)

        return list(query)
