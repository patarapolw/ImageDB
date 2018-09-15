# ImageDB

Store images, especially from Clipboard, in a single file.

## Installation

```commandline
$ pip install imagedb
```

## Usage

```python
>>> from imagedb.app import ImageDB
>>> from IPython.display import HTML, display
>>> db = ImageDB('user/image.db')
>>> image = db.from_clipboard('foo') # Tag as foo
>>> HTML(image.to_html())
An image from clipboard is shown.
>>> for image in db.search()[10:]:
...    db.mark(image, 'bar') # Tag as bar
...    # display(HTML(image.to_html()))
```
