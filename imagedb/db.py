from datetime import datetime
import os

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, select
from sqlalchemy.orm import relationship, deferred

Base = declarative_base()


class Image(Base):
    __tablename__ = 'image'

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False, unique=True)
    info = Column(String, nullable=True, unique=True)
    created = Column(DateTime, default=datetime.now)
    modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    tags = relationship('TagImageConnect', order_by='TagImageConnect.tag_name', back_populates='image')

    def to_html(self):
        from . import config
        return '<img src="{}" />'.format(os.path.join(config['image_db'].db_folder, self.filename))

    def _repr_html_(self):
        return self.to_html()


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

    image = relationship('Image', back_populates='tags')
    tag = relationship('Tag', back_populates='images')
    tag_name = deferred(select([Tag.name]).where(Tag.id == tag_id))
