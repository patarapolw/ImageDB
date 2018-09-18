from flask import Flask
from threading import Thread
import re
import atexit
from send2trash import send2trash
import shutil
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from . import db
from .util import open_browser_tab

__all__ = ('ImageDB', )

app = Flask(__name__)
config = {
    'recent': []
}


class ImageDB:
    def __init__(self, db_path, host='localhost', port='8000', debug=False, runserver=False):
        global config
        config['image_db'] = self

        self.db_folder = os.path.splitext(db_path)[0]

        self.engine = create_engine('sqlite:///' + os.path.abspath(db_path),
                                    connect_args={'check_same_thread': False})
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        if not os.path.exists(db_path):
            db.Base.metadata.create_all(self.engine)

        self.server_thread = None
        if runserver:
            self.runserver(host, port, debug)

        self.recent = []
        atexit.register(self._cleanup)

    def _cleanup(self):
        for stack in self.recent:
            for path in stack['path']:
                send2trash(str(path))

    def runserver(self, host='localhost', port='8000', debug=False):
        open_browser_tab('http://{}:{}'.format(host, port))

        self.server_thread = Thread(target=app.run, kwargs=dict(
            host=host,
            port=port,
            debug=debug
        ))
        self.server_thread.daemon = True
        self.server_thread.start()

    def search(self, tags=None, content=None, type_='partial'):
        def _compare(text, text_compare):
            if type_ == 'partial':
                return text_compare in text
            elif type_ in {'regex', 'regexp', 're'}:
                return re.search(text_compare, text, flags=re.IGNORECASE)
            else:
                return text_compare == text

        def _filter_tag(text_compare, q):
            for db_image in q:
                if any(_compare(tag, text_compare) for tag in db_image.tags):
                    yield db_image

        def _filter_slide(text_compare, q):
            for db_card in q:
                if any(_compare(db_image.info, text_compare) for db_image in q if db_image.info):
                    yield db_card

        query = self.session.query(db.Image).order_by(db.Image.modified.desc())

        if tags:
            if isinstance(tags, str):
                query = _filter_tag(tags, query)
            else:
                for x in tags:
                    query = _filter_tag(x, query)

        if content:
            query = _filter_slide(content, query)

        return list(query)

    def optimize(self):
        paths = set()
        for db_image in self.search():
            if not db_image.exists():
                db_image.delete()
            paths.add(db_image.path)

        for path in Path(self.db_folder).glob('*.*'):
            if path not in paths:
                send2trash(path)

    @staticmethod
    def undo():
        if config['recent']:
            stack = config['recent'][-1]

            for path in stack['path']:
                if path.with_name('_' + path.name).exists():
                    shutil.move(str(path), str(path.with_name('__' + path.name)))
                    shutil.move(str(path.with_name('_' + path.name)),
                                str(path.with_name(path.name)))
                    atexit.register(send2trash,
                                    str(path.with_name('__' + path.name)))

            for db_image in stack['db_images']:
                db_image.versions[-1].revert()


from .views import *
from .api import *
