from datetime import datetime
from pathlib import Path
import shutil
from nonrepeat import nonrepeat_filename
import PIL.Image
import imagehash
from uuid import uuid4
from slugify import slugify

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, select
from sqlalchemy.orm import relationship, deferred
import sqlalchemy
import sqlalchemy_continuum

from .util import shrink_image, trim_image

Base = declarative_base()
sqlalchemy_continuum.make_versioned(user_cls=None)


class Image(Base):
    __versioned__ = {}
    __tablename__ = 'image'

    id = Column(Integer, primary_key=True, autoincrement=True)
    _filename = Column(String, nullable=False, unique=True)
    info = Column(String, nullable=True, unique=True)
    created = Column(DateTime, default=datetime.now)
    modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    image_hash = Column(String, nullable=False, unique=True)

    tag_image_connects = relationship('TagImageConnect', order_by='TagImageConnect.tag_name', back_populates='image')

    def to_json(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'hash': self.image_hash,
            'info': self.info,
            'created': self.created.isoformat(),
            'modified': self.modified.isoformat(),
            'tags': self.tags
        }

    def to_html(self):
        from . import config

        return '<img src="{}" />'.format(str(Path(config['image_db'].db_folder).joinpath(self.filename)))

    def _repr_html_(self):
        return self.to_html()

    def __repr__(self):
        return repr(self.to_json())

    def add_tags(self, tags='marked'):
        """

        :param str|list|tuple tags:
        :return:
        """
        from . import config

        def _mark(tag):
            db_tag = config['image_db'].session.query(Tag).filter_by(name=tag).first()
            if db_tag is None:
                db_tag = Tag()
                db_tag.name = tag

                config['image_db'].session.add(db_tag)
                config['image_db'].session.commit()

            db_tic = config['image_db'].session.query(TagImageConnect).filter_by(tag_id=db_tag.id,
                                                                                 image_id=self.id).first()
            if db_tic is None:
                db_tic = TagImageConnect()
                db_tic.tag_id = db_tag.id
                db_tic.image_id = self.id

                config['image_db'].session.add(db_tic)
                config['image_db'].session.commit()
            else:
                pass
                # raise ValueError('The card is already marked by "{}".'.format(tag))

            return db_tag

        if isinstance(tags, str):
            _mark(tags)
        else:
            for x in tags:
                _mark(x)

    def remove_tags(self, tags='marked'):
        """

        :param str|list|tuple tags:
        :return:
        """
        from . import config

        def _unmark(tag):
            db_tag = config['image_db'].session.query(Tag).filter_by(name=tag).first()
            if db_tag is None:
                raise ValueError('Cannot unmark "{}"'.format(tag))
                # return

            db_tic = config['image_db'].session.query(TagImageConnect).filter_by(tag_id=db_tag.id,
                                                                                 image_id=self.id).first()
            if db_tic is None:
                raise ValueError('Cannot unmark "{}"'.format(tag))
                # return
            else:
                config['image_db'].session.delete(db_tic)
                config['image_db'].session.commit()

            return db_tag

        if isinstance(tags, str):
            _unmark(tags)
        else:
            for x in tags:
                _unmark(x)

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, new_filename):
        from . import config

        if self.filename:
            if self.filename != new_filename:
                new_filename = Path(new_filename)
                new_filename = new_filename \
                    .with_name(new_filename.name)\
                    .with_suffix(self.path.suffix)
                new_filename = nonrepeat_filename(str(new_filename),
                                                  primary_suffix='-'.join(self.tags),
                                                  root=config['image_db'].db_folder)

                true_filename = Path(config['image_db'].db_folder).joinpath(new_filename)
                true_filename.parent.mkdir(parents=True, exist_ok=True)

                shutil.move(str(self.path), str(true_filename))
                self._filename = new_filename
            else:
                pass
        else:
            self._filename = new_filename
            config['image_db'].session.add(self)
            config['image_db'].session.commit()

    @property
    def tags(self):
        return [tic.tag.name for tic in self.tag_image_connects]

    @classmethod
    def from_bytes_io(cls, im_bytes_io, filename=None, tags=None):
        """

        :param im_bytes_io:
        :param str filename:
        :param str|list|tuple tags:
        :return:
        """
        from . import config

        image_path = Path(config['image_db'].db_folder)

        if not filename or filename == 'image.png':
            filename = 'blob/' + str(uuid4())[:8] + '.png'
            image_path.joinpath('blob').mkdir(parents=True, exist_ok=True)
        else:
            image_path.mkdir(parents=True, exist_ok=True)

        filename = str(image_path.joinpath(filename)
                       .relative_to(config['image_db'].db_folder))
        filename = nonrepeat_filename(filename,
                                      primary_suffix=slugify('-'.join(tags)),
                                      root=str(image_path))

        true_filename = str(image_path.joinpath(filename))
        im = PIL.Image.open(im_bytes_io)
        im = trim_image(im)
        im = shrink_image(im)

        h = str(imagehash.dhash(im))
        pre_existing = config['image_db'].session.query(cls).filter_by(image_hash=h).first()
        if pre_existing is not None:
            raise ValueError('Similar image exists: {}'.format(pre_existing.path))
        else:
            im.save(true_filename)

            db_image = cls()
            db_image._filename = filename
            db_image.image_hash = h
            config['image_db'].session.add(db_image)
            config['image_db'].session.commit()

            if tags:
                db_image.add_tags(tags)

            return db_image

    def delete(self, delete_stack=None):
        from . import config

        if delete_stack is None:
            delete_stack = list()

        for tic in self.tag_image_connects:
            config['image_db'].session.delete(tic)
            config['image_db'].session.commit()

        config['image_db'].session.delete(self)
        config['image_db'].session.commit()
        if self.exists():
            if delete_stack:
                delete_stack.append(self.path)
            else:
                shutil.move(self.path, self.path.with_name('_' + self.path.name))

        return delete_stack

    def exists(self):
        return self.path.exists()

    @property
    def path(self):
        from . import config

        return Path(config['image_db'].db_folder).joinpath(self.filename)

    def v_join(self, db_images):
        """

        :param list db_images:
        :return:
        """
        from . import config

        if not any(self.id == db_image.id for db_image in db_images):
            db_images.insert(0, self)

        pil_images = list(map(PIL.Image.open, (db_image.path for db_image in db_images)))
        widths, heights = zip(*(i.size for i in pil_images))

        max_width = max(widths)
        total_height = sum(heights)
        new_im = PIL.Image.new('RGBA', (max_width, total_height))

        y_offset = 0
        for i, im in enumerate(pil_images):
            new_im.paste(im, (0, y_offset))
            y_offset += heights[i]

        temp_path = str(self.path.with_name('_' + self.path.name))
        shutil.move(src=str(self.path), dst=str(temp_path))
        delete_stack = [temp_path]

        new_im.save(self.path)

        for db_image in db_images:
            if self.id != db_image.id:
                delete_stack = db_image.delete(delete_stack)

        config['recent'].append({
            'db_images': db_images,
            'delete': delete_stack
        })

        return self

    def h_join(self, db_images):
        """

        :param list db_images:
        :return:
        """
        from . import config

        if not any(self.id == db_image.id for db_image in db_images):
            db_images.insert(self, 0)

        pil_images = list(map(PIL.Image.open, (db_image.path for db_image in db_images)))
        widths, heights = zip(*(i.size for i in pil_images))

        total_width = sum(widths)
        max_height = max(heights)
        new_im = PIL.Image.new('RGBA', (total_width, max_height))

        x_offset = 0
        for i, im in enumerate(pil_images):
            new_im.paste(im, (x_offset, 0))
            im.close()
            x_offset += widths[i]

        temp_path = nonrepeat_filename(str(self.path))
        shutil.move(src=str(self.path), dst=str(temp_path))
        delete_stack = [temp_path]

        new_im.save(self.path)

        for db_image in db_images:
            if self.id != db_image.id:
                delete_stack = db_image.delete(delete_stack)

        config['recent'].append({
            'db_images': db_images,
            'delete': delete_stack
        })

        return self

    def undo(self):
        import atexit
        from send2trash import send2trash

        if self.versions:
            if self.path.with_name('_' + self.path.name).exists():
                shutil.move(str(self.path), str(self.path.with_name('__' + self.path.name)))
                shutil.move(str(self.path.with_name('_' + self.path.name)),
                            str(self.path))
                atexit.register(send2trash,
                                str(self.path.with_name('__' + self.path.name)))

            self.version[-1].revert()


class Tag(Base):
    __tablename__ = 'tag'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)

    tag_image_connects = relationship('TagImageConnect', order_by='TagImageConnect.id', back_populates='tag')

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'images': [tic.image.to_json() for tic in self.tag_image_connects]
        }

    def __repr__(self):
        return repr(self.to_json())


class TagImageConnect(Base):
    __tablename__ = 'tag_image_connect'

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey('image.id'), nullable=False)
    tag_id = Column(Integer, ForeignKey('tag.id'), nullable=False)

    image = relationship('Image', back_populates='tag_image_connects')
    tag = relationship('Tag', back_populates='tag_image_connects')
    tag_name = deferred(select([Tag.name]).where(Tag.id == tag_id))

    def to_json(self):
        return {
            'id': self.id,
            'image': self.image.to_json(),
            'tag': self.tag.name
        }

    def __repr__(self):
        return repr(self.to_json())


sqlalchemy.orm.configure_mappers()
