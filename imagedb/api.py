from flask import request, jsonify, Response
from werkzeug.utils import secure_filename

from pathlib import Path
from nonrepeat import nonrepeat_filename
import shutil
from slugify import slugify
from uuid import uuid4

from . import app, db, config

filename = None


@app.route('/api/images/create', methods=['POST'])
def create_image():
    global filename

    if 'file' in request.files:
        image_path = Path(config['image_db'].db_folder).joinpath(request.form.get('imagePath'))
        tags = request.form.get('tags')
        if image_path.suffix:
            image_path = image_path.parent

        file = request.files['file']
        if file.filename == 'image.png':
            filename = 'blob/' + str(uuid4()) + '.png'
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
        config['image_db'].mark(db_image, tags)

        config['image_db'].session.add(db_image)
        config['image_db'].session.commit()

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

    db_image = config['image_db'].session.query(db.Image).filter_by(filename=filename).first()

    if filename is not None and db_image is not None:
        post_json = request.get_json()

        new_filename = Path(post_json['filename'])\
            .with_suffix(Path(filename).suffix)
        new_filename.parent.mkdir(parents=True, exist_ok=True)

        new_filename = new_filename.with_name(secure_filename(new_filename.name))
        new_filename = nonrepeat_filename(str(new_filename),
                                          root=config['image_db'].db_folder)

        true_filename = str(Path(config['image_db'].db_folder).joinpath(new_filename))

        shutil.move(str(Path(config['image_db'].db_folder).joinpath(filename)),
                    true_filename)
        filename = new_filename

        db_image.filename = filename
        config['image_db'].mark(db_image, post_json['tags'])
        config['image_db'].session.commit()

        return jsonify({
            'filename': filename,
            'trueFilename': true_filename
        }), 201

    return Response(status=304)
