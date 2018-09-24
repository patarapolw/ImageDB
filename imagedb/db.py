from datetime import datetime
from pathlib import Path
import shutil
from nonrepeat import nonrepeat_filename
import PIL.Image
import imagehash
from uuid import uuid4
from slugify import slugify
import logging
import base64
import os
from urllib.parse import quote

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, select
from sqlalchemy.orm import relationship, deferred

from .util import shrink_image, trim_image, HAlign, VAlign
from .config import config

Base = declarative_base()

SIMILARITY_THRESHOLD = 3


class Image(Base):
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

    @property
    def url(self):
        return 'http://{}:{}/images?filename={}&time={}'.format(
            os.getenv('HOST', 'localhost'),
            os.getenv('PORT', '8000'),
            quote(str(self.path), safe=''),
            quote(datetime.now().isoformat())
        )

    def to_base64(self):
        with self.path.open('rb') as f:
            base64_str = base64.b64encode(f.read()).decode()

        return '<img src="data:image/png;base64,{}" />'.format(base64_str)

    def to_relative_path(self):
        return '<img src="{}" />'.format(str(self.path.relative_to('.')))

    def to_url(self):
        return '<img src="{}" />'.format(self.url)

    def _repr_html_(self):
        if os.getenv('IMAGE_SERVER', '1') == '1':
            return self.to_url()
        else:
            return self.to_base64()

    # def __repr__(self):
    #     return repr(self.to_json())

    def add_tags(self, tags='marked'):
        """

        :param str|list|tuple tags:
        :return:
        """
        def _mark(tag):
            db_tag = config['session'].query(Tag).filter_by(name=tag).first()
            if db_tag is None:
                db_tag = Tag()
                db_tag.name = tag

                config['session'].add(db_tag)
                config['session'].commit()

            db_tic = config['session'].query(TagImageConnect).filter_by(tag_id=db_tag.id,
                                                                                 image_id=self.id).first()
            if db_tic is None:
                db_tic = TagImageConnect()
                db_tic.tag_id = db_tag.id
                db_tic.image_id = self.id

                config['session'].add(db_tic)
                config['session'].commit()
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
        def _unmark(tag):
            db_tag = config['session'].query(Tag).filter_by(name=tag).first()
            if db_tag is None:
                raise ValueError('Cannot unmark "{}"'.format(tag))
                # return

            db_tic = config['session'].query(TagImageConnect).filter_by(tag_id=db_tag.id,
                                                                                 image_id=self.id).first()
            if db_tic is None:
                raise ValueError('Cannot unmark "{}"'.format(tag))
                # return
            else:
                config['session'].delete(db_tic)
                config['session'].commit()

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
        if self.filename:
            if self.filename != new_filename:
                new_filename = Path(new_filename)
                new_filename = new_filename \
                    .with_name(new_filename.name)\
                    .with_suffix(self.path.suffix)
                new_filename = nonrepeat_filename(str(new_filename),
                                                  primary_suffix='-'.join(self.tags),
                                                  root=config['folder'])

                true_filename = Path(config['folder']).joinpath(new_filename)
                true_filename.parent.mkdir(parents=True, exist_ok=True)

                shutil.move(str(self.path), str(true_filename))

                config['recent'].append({
                    # 'db': [self.versions[0]],
                    'moved': [(str(self.path), str(true_filename))]
                })

                self._filename = new_filename
                config['session'].commit()
            else:
                pass
        else:
            self._filename = new_filename
            config['session'].add(self)
            config['session'].commit()

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
        if not filename or filename == 'image.png':
            filename = 'blob/' + str(uuid4())[:8] + '.png'

        image_path = Path(config['folder'])
        image_path.joinpath(filename).parent.mkdir(parents=True, exist_ok=True)

        filename = str(image_path.joinpath(filename)
                       .relative_to(config['folder']))
        filename = nonrepeat_filename(filename,
                                      primary_suffix=slugify('-'.join(tags)),
                                      root=str(image_path))

        return cls._create(filename, tags=tags, pil_handle=im_bytes_io)

    @classmethod
    def from_existing(cls, abs_path, rel_path=None, tags=None):
        if rel_path is None:
            try:
                rel_path = abs_path.relative_to(config['folder'])
            except ValueError:
                rel_path = Path(abs_path.name)

        return cls._create(filename=str(rel_path), tags=tags, pil_handle=abs_path)

    @classmethod
    def _create(cls, filename, tags, pil_handle):
        image_path = Path(config['folder'])
        image_path.joinpath(filename).parent.mkdir(parents=True, exist_ok=True)

        true_filename = image_path.joinpath(filename)
        do_save = True
        if true_filename.exists():
            do_save = False

        im = PIL.Image.open(pil_handle)
        im = trim_image(im)
        im = shrink_image(im)

        h = str(imagehash.dhash(im))
        try:
            pre_existing = next(cls.similar_images_by_hash(h))
            pre_existing.modified = datetime.now()
            config['session'].commit()

            err_msg = 'Similar image exists: {}'.format(pre_existing.path)
            # raise ValueError(err_msg)
            logging.error(err_msg)
            return err_msg

        except StopIteration:
            if do_save:
                im.save(true_filename)

            db_image = cls()
            db_image._filename = filename
            db_image.image_hash = h
            config['session'].add(db_image)
            config['session'].commit()

            if tags:
                db_image.add_tags(tags)

            return db_image

    def delete(self, recent_items=None):
        if recent_items is None:
            recent_items = dict()

        for tic in self.tag_image_connects:
            # recent_items.setdefault('db', []).append(tic.versions[0])

            config['session'].delete(tic)
            config['session'].commit()

        # recent_items.setdefault('db', []).append(self.versions[0])

        config['session'].delete(self)
        config['session'].commit()

        if self.exists():
            to_delete = self.path.with_name('_' + self.path.name)
            shutil.move(str(self.path), str(to_delete))
            if 'deleted' in recent_items.keys():
                recent_items['deleted'].append(to_delete)
            else:
                recent_items['deleted'] = [to_delete]
                config['recent'].append(recent_items)

        return recent_items

    def exists(self):
        return self.path.exists()

    @property
    def path(self):
        return Path(config['folder']).joinpath(self.filename)

    @path.setter
    def path(self, file_path):
        self._filename = file_path.relative_to(Path(config['folder']))

    def v_join(self, db_images, h_align=HAlign.CENTER):
        return self._join(db_images, h_align=h_align, v_align=None)

    def h_join(self, db_images, v_align=VAlign.MIDDLE):
        return self._join(db_images, h_align=None, v_align=v_align)

    def _join(self, db_images, h_align=None, v_align=None):
        if not any(self.id == db_image.id for db_image in db_images):
            db_images.insert(0, self)

        pil_images = list(map(PIL.Image.open, (db_image.path for db_image in db_images)))
        widths, heights = zip(*(i.size for i in pil_images))

        max_height = None
        max_width = None
        total_width = None
        total_height = None
        x_offset = 0
        y_offset = 0
        if v_align:
            total_width = sum(widths)
            max_height = max(heights)
            new_im = PIL.Image.new('RGBA', (total_width, max_height))
        else:
            max_width = max(widths)
            total_height = sum(heights)
            new_im = PIL.Image.new('RGBA', (max_width, total_height))

        for im in pil_images:
            w, h = im.size

            if v_align:
                y_offset = {
                    VAlign.TOP.value: 0,
                    VAlign.MIDDLE.value: (max_height - h) / 2,
                    VAlign.BOTTOM.value: max_height - h
                }.get(getattr(v_align, 'value', v_align), 0)
            else:
                x_offset = {
                    HAlign.LEFT.value: 0,
                    HAlign.CENTER.value: (max_width - w) / 2,
                    HAlign.RIGHT.value: max_width - w
                }.get(getattr(h_align, 'value', h_align), 0)

            new_im.paste(im, (int(x_offset), int(y_offset)))

            if v_align:
                x_offset += w
            else:
                y_offset += h

        assert x_offset == total_width or y_offset == total_height

        temp_path = self.path.with_name('_' + self.path.name)
        shutil.move(src=str(self.path), dst=str(temp_path))

        new_im.save(self.path)

        recent_items = {
            'deleted': [temp_path]
        }

        for db_image in db_images:
            if self.id != db_image.id:
                self.add_tags(db_image.tags)
                recent_items = db_image.delete(recent_items)

        config['recent'].append(recent_items)

        return self

    @classmethod
    def similar_images_by_hash(cls, h):
        for db_image in config['session'].query(cls).all():
            if imagehash.hex_to_hash(db_image.image_hash) - imagehash.hex_to_hash(h) < SIMILARITY_THRESHOLD:
                yield db_image

    @classmethod
    def similar_images(cls, im):
        h = str(imagehash.dhash(im))

        yield from cls.similar_images_by_hash(h)

    def replace_with(self, newer_db_image):
        recent_items = {
            # 'db': [self.versions[0], newer_db_image.versions[0]],
            'deleted': [self.path.with_name('_' + self.path.name)],
            'moved': [(str(newer_db_image.path), str(self.path))]
        }

        shutil.move(str(self.path), str(self.path.with_name('_' + self.path.name)))
        shutil.move(str(newer_db_image.path), str(self.path))
        
        self._filename = newer_db_image.filename
        config['session'].delete(newer_db_image)
        config['session'].commit()
        config['recent'].append(recent_items)

        return self


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
