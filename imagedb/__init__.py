from flask import Flask
from threading import Thread
import re

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from . import db
from .util import open_browser_tab

app = Flask(__name__)
config = dict()


class ImageDB:
    def __init__(self, db_path, host='localhost', port='8000', debug=False):
        global config
        config['image_db'] = self

        self.db_folder = os.path.splitext(db_path)[0]

        self.engine = create_engine('sqlite:///' + db_path, connect_args={'check_same_thread': False})
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        if not os.path.exists(db_path):
            db.Base.metadata.create_all(self.engine)

        self._run_server(host, port, debug)

    @staticmethod
    def _run_server(host='localhost', port='8000', debug=False):
        open_browser_tab('http://{}:{}'.format(host, port))

        app_thread = Thread(target=app.run, kwargs=dict(
            host=host,
            port=port,
            debug=debug
        ))
        app_thread.daemon = True
        app_thread.start()

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


from .views import *
from .api import *
