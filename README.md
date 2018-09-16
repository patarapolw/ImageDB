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
