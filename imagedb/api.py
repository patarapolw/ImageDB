from flask import request, jsonify, Response
from werkzeug.utils import secure_filename

from io import BytesIO

from . import app, db, config

filename = None


@app.route('/api/images/create', methods=['POST'])
def create_image():
    global filename

    if 'file' in request.files:
        tags = request.form.get('tags')
        file = request.files['file']
        with BytesIO() as bytes_io:
            file.save(bytes_io)
            db_image = db.Image.from_bytes_io(bytes_io,
                                              filename=secure_filename(file.filename), tags=tags)

            filename = db_image.filename

            return jsonify({
                'filename': db_image.filename,
                'trueFilename': str(db_image.path)
            }), 201

    return Response(status=304)


@app.route('/api/images/rename', methods=['POST'])
def rename_image():
    global filename

    db_image = config['image_db'].session.query(db.Image).filter_by(_filename=filename).first()
    if filename is not None and db_image is not None:
        post_json = request.get_json()
        db_image.add_tags(post_json['tags'])
        db_image.filename = post_json['filename']

        return jsonify({
            'filename': db_image.filename,
            'trueFilename': str(db_image.path)
        }), 201

    return Response(status=304)
