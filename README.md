# ImageDB

Store images, especially from Clipboard, in database.

## Installation

```commandline
$ pip install imagedb
```

## Usage

```python
>>> from imagedb.app import ImageDB
>>> from IPython.display import HTML, display
>>> image_db = ImageDB('image.db')
>>> image_db.run_server()
An image server for the database is run.
>>> for image in db.search()[10:]:
...    db.mark(image, 'bar') # Tag as bar
...    # display(HTML(image.to_html()))
```

## Screenshots

<img src="https://raw.githubusercontent.com/patarapolw/ImageDB/master/screenshots/jupyter1.png" />
<img src="https://raw.githubusercontent.com/patarapolw/ImageDB/master/screenshots/jupyter2.png" />
<img src="https://raw.githubusercontent.com/patarapolw/ImageDB/master/screenshots/browser1.png" />
<img src="https://raw.githubusercontent.com/patarapolw/ImageDB/master/screenshots/browser2.png" />
