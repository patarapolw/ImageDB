from flask import render_template, send_file, request
import os
from urllib.parse import unquote

from . import app


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/images')
def get_image():
    return send_file(os.path.abspath(unquote(request.args.get('filename'))))
