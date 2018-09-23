# ImageDB

Store images, especially from Clipboard, in a database, and spin an image server (for usage in Jupyter Notebook).

## Installation

```commandline
$ pip install imagedb
```

Or

1. Clone the project from GitHub
2. `poetry add imagedb --path path/to/imagedb/folder`

## Usage

### Run an image server

In a Python script (outside Jupyter Notebook).

```python
from imagedb import ImageDB
ImageDB('images.db').runserver()
# Then, go to `http://localhost:8000` in your browser to register an image (from the clipboard).
```

### Get images from the image server

In Jupyter Notebook

```pydocstring
>>> from imagedb import ImageDB
>>> idb = ImageDB('images.db')
>>> idb.last()
# The latest image in the server will be shown.  `idb.last(5)` is also supported.
>>> from IPython.display import display
>>> for image in idb.search(tags='bar'):
...     display(image)
# All images corresponding to the tag 'bar' will be shown.
```

## Screenshots

<img src="https://raw.githubusercontent.com/patarapolw/ImageDB/master/screenshots/jupyter1.png" />
<img src="https://raw.githubusercontent.com/patarapolw/ImageDB/master/screenshots/jupyter2.png" />
<img src="https://raw.githubusercontent.com/patarapolw/ImageDB/master/screenshots/browser1.png" />
<img src="https://raw.githubusercontent.com/patarapolw/ImageDB/master/screenshots/browser2.png" />
