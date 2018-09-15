from datetime import datetime
import base64

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Binary, DateTime, Enum, ForeignKey, select
from sqlalchemy.orm import relationship, deferred

Base = declarative_base()


class Image(Base):
    __tablename__ = 'image'

    id = Column(Integer, primary_key=True, autoincrement=True)
    data = Column(Binary, nullable=True)
    info = Column(String, nullable=True, unique=True)
    created = Column(DateTime, default=datetime.now)
    modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    tags = relationship('TagImageConnect', order_by='TagImageConnect.tag_name', back_populates='image')

    def to_html(self):
        return '<img src="data:image/png;base64,' + base64.b64encode(self.data).decode() + '" />'

    def _repr_html_(self):
        if self.data:
            return self.to_html()
        else:
            return self.info

    def save(self, filename):
        with open(filename, 'wb') as f:
            f.write(self.data)


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
