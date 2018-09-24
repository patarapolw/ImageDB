from threading import Thread
import re
import atexit
from send2trash import send2trash
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from IPython.display import display
import sys
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from . import db, app
from .util import open_browser_tab
from .config import config


class ImageDB:
    def __init__(self, db_path, host='localhost', port='8000', debug=False, runserver=False):
        os.environ.update({
            'HOST': host,
            'PORT': port,
            'DEBUG': '1' if debug else '0',
            'IMAGE_SERVER': '1'
        })

        self.folder = os.path.splitext(db_path)[0]

        self.engine = create_engine('sqlite:///' + os.path.abspath(db_path),
                                    connect_args={'check_same_thread': False})
        self.session = sessionmaker(bind=self.engine)()

        if not os.path.exists(db_path):
            db.Base.metadata.create_all(self.engine)

        self.server_thread = None
        if runserver:
            self.runserver()

        atexit.register(self._cleanup)

        config.update({
            'session': self.session,
            'folder': self.folder
        })

    @staticmethod
    def _cleanup():
        for stack in config['recent']:
            for path in stack['deleted']:
                send2trash(str(path))

    def runserver(self):
        def _runserver():
            app.run(
                host=os.getenv('HOST', 'localhost'),
                port=os.getenv('PORT', '8000'),
                debug=True if os.getenv('DEBUG', '0') == '1' else False
            )

        def _runserver_in_thread():
            open_browser_tab('http://{}:{}'.format(
                os.getenv('HOST', 'localhost'),
                os.getenv('PORT', '8000')
            ))
            self.server_thread = Thread(target=_runserver)
            self.server_thread.daemon = True
            self.server_thread.start()

        if 'ipykernel' in ' '.join(sys.argv):
            _runserver_in_thread()
        elif os.getenv('THREADED_IMAGE_SERVER', '0') == '1':
            _runserver_in_thread()
        else:
            _runserver()

    def search(self, filename=None, tags=None, content=None,
               type_='partial', since=None, until=None,
               filename_regex=None):
        def _compare(text, text_compare):
            if type_ == 'partial':
                return text_compare in text
            elif type_ in {'regex', 'regexp', 're'}:
                return re.search(text_compare, text, flags=re.IGNORECASE)
            else:
                return text_compare == text

        def _filter_filename(text_compare, q):
            for db_image in q:
                if any(_compare(tag, text_compare) for tag in db_image.filename):
                    yield db_image

        def _filter_tag(text_compare, q):
            for db_image in q:
                if any(_compare(tag, text_compare) for tag in db_image.tags):
                    yield db_image

        def _filter_slide(text_compare, q):
            for db_card in q:
                if any(_compare(db_image.info, text_compare) for db_image in q if db_image.info):
                    yield db_card

        query = self.session.query(db.Image)
        if since:
            if isinstance(since, timedelta):
                since = datetime.now() - since
            query = query.filter(db.Image.modified > since)
        if until:
            query = query.filter(db.Image.modified < until)

        query = iter(query.order_by(db.Image.modified.desc()))

        if tags:
            if isinstance(tags, str):
                query = _filter_tag(tags, query)
            else:
                for x in tags:
                    query = _filter_tag(x, query)

        if content:
            query = _filter_slide(content, query)

        if filename_regex:
            filename = filename_regex
            type_ = 're'

        if filename:
            query = _filter_filename(filename, query)

        return query

    def search_filename(self, filename_regex):
        for path in Path(self.folder).glob('**/*.*'):
            if path.suffix.lower() in {'.png', '.jpg', '.jp2', '.jpeg', '.gif'}:
                if re.search(filename_regex, str(path), re.IGNORECASE):
                    db_image = db.Image()
                    db_image.path = path

                    yield db_image

    def optimize(self):
        paths = set()
        for db_image in self.search():
            if not db_image.exists():
                print(db_image)
                db_image.delete()
            else:
                paths.add(db_image.path)

        for path in Path(self.folder).glob('**/*.*'):
            if path.suffix.lower() in {'.png', '.jpg', '.jp2', '.jpeg', '.gif'}:
                if path not in paths:
                    print(path)
                    send2trash(str(path))

    def undo(self):
        if len(config['recent']) > 0:
            stack = config['recent'].pop()

            for path in stack.get('deleted', []):
                path = Path(path)
                if path.name[0] == '_':
                    if path.with_name(path.name[1:]).exists():
                        shutil.move(str(path.with_name(path.name[1:])), str(path.with_name('_' + path.name)))
                        atexit.register(send2trash,
                                        str(path.with_name('_' + path.name)))
                    shutil.move(str(path), str(path.with_name(path.name[1:])))

            for src, dst in stack.get('moved', []):
                shutil.move(src=dst, dst=src)

            self.session.commit()

    def last(self, count=1):
        for i, db_image in enumerate(self.search()):
            if i >= count:
                break
            display(db_image)

    def import_images(self, file_path=None, tags=None):
        if file_path is None:
            file_path = self.folder

        for p in Path(file_path).glob('**/*.*'):
            if p.suffix.lower() in {'.png', '.jpg', '.jp2', '.jpeg', '.gif'}:
                db.Image.from_existing(p, tags=tags)
