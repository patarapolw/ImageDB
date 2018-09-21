import click
import os

from imagedb import ImageDB


@click.command()
@click.option('--path', envvar='IMAGE_PATH')
@click.option('--host', envvar='HOST', default='localhost')
@click.option('--port', envvar='PORT', default='8000')
@click.option('--debug', is_flag=True)
def cli(db_path, host='localhost', port='8000', debug=False):
    os.environ['IMAGE_SERVER'] = '1'
    ImageDB(
        db_path=db_path,
        host=host,
        port=port,
        debug=debug,
        runserver=True
    )
