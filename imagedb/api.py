from flask import request, jsonify, Response
from werkzeug.utils import secure_filename

from pathlib import Path
from nonrepeat import nonrepeat_filename
from slugify import slugify
from uuid import uuid4

from . import app, db, config

filename = None


@app.route('/api/images/create', methods=['POST'])
def create_image():
    global filename

    if 'file' in request.files:
        image_path = Path(config['image_db'].db_folder)
        tags = request.form.get('tags')
        if image_path.suffix:
            image_path = image_path.parent

        file = request.files['file']
        if file.filename == 'image.png':
            filename = 'blob/' + str(uuid4())[:8] + '.png'
            image_path.joinpath('blob').mkdir(parents=True, exist_ok=True)
        else:
            filename = secure_filename(file.filename)
            image_path.mkdir(parents=True, exist_ok=True)

        filename = str(image_path.joinpath(filename)
                       .relative_to(config['image_db'].db_folder))
        filename = nonrepeat_filename(filename,
                                      primary_suffix=slugify('-'.join(tags)),
                                      root=str(image_path))
        db_image = db.Image()
        db_image.filename = filename
        filename = db_image.filename

        db_image.add_tags(tags)

        true_filename = str(image_path.joinpath(filename))
        file.save(true_filename)

        return jsonify({
            'filename': filename,
            'trueFilename': true_filename
        }), 201

    return Response(status=304)


@app.route('/api/images/rename', methods=['POST'])
def rename_image():
    global filename

    db_image = config['image_db'].session.query(db.Image).filter_by(_filename=filename).first()

    if filename is not None and db_image is not None:
        post_json = request.get_json()

        db_image.add_tags(post_json['tags'])
        config['image_db'].session.commit()

        new_filename = str(Path(post_json['filename']).with_suffix(Path(filename).suffix))

        db_image.filename = new_filename
        filename = db_image.filename

        true_filename = str(Path(config['image_db'].db_folder).joinpath(filename))

        return jsonify({
            'filename': filename,
            'trueFilename': true_filename
        }), 201

    return Response(status=304)
