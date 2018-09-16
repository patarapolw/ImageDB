from datetime import datetime
from pathlib import Path
import shutil
from nonrepeat import nonrepeat_filename

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, select
from sqlalchemy.orm import relationship, deferred

Base = declarative_base()


class Image(Base):
    __tablename__ = 'image'

    id = Column(Integer, primary_key=True, autoincrement=True)
    _filename = Column(String, nullable=False, unique=True)
    info = Column(String, nullable=True, unique=True)
    created = Column(DateTime, default=datetime.now)
    modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    _tags = relationship('TagImageConnect', order_by='TagImageConnect.tag_name', back_populates='image')

    def to_json(self):
        return {
            'id': self.id,
            'filename': self.filename,
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

    def add_tags(self, tag_or_tags='marked'):
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
                db_tic.card_id = db_tic.id

                config['image_db'].session.add(db_tic)
                config['image_db'].session.commit()
            else:
                pass
                # raise ValueError('The card is already marked by "{}".'.format(tag))

            return db_tag

        if isinstance(tag_or_tags, str):
            yield _mark(tag_or_tags)
        else:
            for x in tag_or_tags:
                yield _mark(x)

    def remove_tags(self, tag_or_tags='marked'):
        from . import config

        def _unmark(tag):
            db_tag = config['image_db'].session.query(Tag).filter_by(name=tag).first()
            if db_tag is None:
                raise ValueError('Cannot unmark "{}"'.format(tag))
                # return

            db_tic = config['image_db'].session.query(TagImageConnect).filter_by(tag_id=db_tag.id,
                                                                                 card_id=self.id).first()
            if db_tic is None:
                raise ValueError('Cannot unmark "{}"'.format(tag))
                # return
            else:
                config['image_db'].session.delete(db_tic)
                config['image_db'].session.commit()

            yield db_tag

        if isinstance(tag_or_tags, str):
            yield _unmark(tag_or_tags)
        else:
            for x in tag_or_tags:
                yield _unmark(x)

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, new_filename):
        from . import config

        if self.filename:
            new_filename = Path(new_filename)
            new_filename = new_filename\
                .with_suffix(Path(self._filename).suffix)\
                .with_name(new_filename.name)
            new_filename = nonrepeat_filename(str(new_filename),
                                              primary_suffix='-'.join(self.tags),
                                              root=config['image_db'].db_folder)

            true_filename = Path(config['image_db'].db_folder).joinpath(new_filename)
            true_filename.parent.mkdir(parents=True, exist_ok=True)
            true_filename = str(true_filename)

            shutil.move(str(Path(config['image_db'].db_folder).joinpath(self._filename)),
                        true_filename)
            self._filename = new_filename
        else:
            self._filename = new_filename
            config['image_db'].session.add(self)

        config['image_db'].session.commit()

    @property
    def tags(self):
        return [tag.tag_name for tag in self._tags]

    def delete(self):
        from . import config

        config['image_db'].session.delete(self)
        Path(config['image_db'].db_folder).joinpath(self.filename).unlink()


class Tag(Base):
    __tablename__ = 'tag'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)

    images = relationship('TagImageConnect', order_by='TagImageConnect.id', back_populates='tag')


class TagImageConnect(Base):
    __tablename__ = 'tag_image_connect'

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey('image.id'), nullable=False)
    tag_id = Column(Integer, ForeignKey('tag.id'), nullable=False)

    image = relationship('Image', back_populates='_tags')
    tag = relationship('Tag', back_populates='images')
    tag_name = deferred(select([Tag.name]).where(Tag.id == tag_id))
