"Command line interface to the DataGraphics instance."

import json
import os.path
import time

import click
import couchdb2
import flask

import datagraphics.config
import datagraphics.user

from datagraphics import constants
from datagraphics import utils


@click.group()
def cli():
    "Command line interface to the DataGraphics instance."
    pass


@cli.command()
@click.option(
    "-s",
    "--silent",
    is_flag=True,
    default=False,
    help="Do not complain if database already exists.",
)
def create_database(silent):
    "Create the database instance within CouchDB. Load the design documents."
    app = datagraphics.config.create_app(__name__, init_db=False)
    with app.app_context():
        server = utils.get_server(app=app)
        if app.config["COUCHDB_DBNAME"] in server:
            if not silent:
                raise click.ClickException(
                    f"""Database '{app.config["COUCHDB_DBNAME"]}' already exists."""
                )
        else:
            server.create(app.config["COUCHDB_DBNAME"])
            click.echo(f"""Created database '{app.config["COUCHDB_DBNAME"]}'.""")
        datagraphics.config.load_db_designs(app)


@cli.command()
def destroy_database():
    "Hard delete of the entire database, including the instance within CouchDB."
    app = datagraphics.config.create_app(__name__, init_db=False)
    with app.app_context():
        server = utils.get_server(app=app)
        try:
            db = server[app.config["COUCHDB_DBNAME"]]
        except couchdb2.NotFoundError as error:
            raise click.ClickException(str(error))
        db.destroy()
        click.echo(f"""Destroyed database '{app.config["COUCHDB_DBNAME"]}'.""")


@cli.command()
def counts():
    "Output counts of entities in the system."
    app = datagraphics.config.create_app(__name__)
    with app.app_context():
        utils.set_db()
        click.echo(f"{utils.get_count('users', 'username'):>5} users")
        click.echo(f"{utils.get_count('datasets', 'owner_modified'):>5} datasets")
        click.echo(f"{utils.get_count('graphics', 'owner_modified'):>5} graphics")


@cli.command()
@click.option("--username", help="Username for the new admin account.", prompt=True)
@click.option("--email", help="Email address for the new admin account.", prompt=True)
@click.option(
    "--password",
    help="Password for the new admin account.",
    prompt=True,
    hide_input=True,
)
def create_admin(username, email, password):
    "Create a new admin account."
    app = datagraphics.config.create_app(__name__)
    with app.app_context():
        utils.set_db()
        try:
            with datagraphics.user.UserSaver() as saver:
                saver.set_username(username)
                saver.set_email(email)
                saver.set_password(password)
                saver.set_apikey()
                saver.set_role(constants.ADMIN)
                saver.set_status(constants.ENABLED)
        except ValueError as error:
            raise click.ClickException(str(error))


@cli.command()
@click.option("--username", help="Username for the new user account.", prompt=True)
@click.option("--email", help="Email address for the new user account.", prompt=True)
@click.option(
    "--password",
    help="Password for the new user account.",
    prompt=True,
    hide_input=True,
)
def create_user(username, email, password):
    "Create a new user account."
    app = datagraphics.config.create_app(__name__)
    with app.app_context():
        utils.set_db()
        try:
            with datagraphics.user.UserSaver() as saver:
                saver.set_username(username)
                saver.set_email(email)
                saver.set_password(password)
                saver.set_apikey()
                saver.set_role(constants.USER)
                saver.set_status(constants.ENABLED)
        except ValueError as error:
            raise click.ClickException(str(error))


@cli.command()
@click.option("--username", help="Username for the user account.", prompt=True)
@click.option(
    "--password",
    help="New password for the user account.",
    prompt=True,
    hide_input=True,
)
def password(username, password):
    "Set the password for a user account."
    app = datagraphics.config.create_app(__name__)
    with app.app_context():
        utils.set_db()
        user = datagraphics.user.get_user(username=username)
        if user:
            with datagraphics.user.UserSaver(user) as saver:
                saver.set_password(password)
        else:
            raise click.ClickException("No such user.")


@cli.command()
@click.option(
    "-d",
    "--dumpfile",
    type=str,
    help="The path of the DataGraphics database dump file.",
)
@click.option(
    "-D",
    "--dumpdir",
    type=str,
    help="The directory to write the dump file in, using the default name.",
)
@click.option(
    "--progressbar/--no-progressbar", default=True, help="Display a progressbar."
)
def dump(dumpfile, dumpdir, progressbar):
    "Dump all data in the database to a .tar.gz dump file."
    app = datagraphics.config.create_app(__name__)
    with app.app_context():
        utils.set_db()
        if not dumpfile:
            dumpfile = "dump_{0}.tar.gz".format(time.strftime("%Y-%m-%d"))
            if dumpdir:
                dumpfile = os.path.join(dumpdir, dumpfile)
        ndocs, nfiles = flask.g.db.dump(
            dumpfile, exclude_designs=True, progressbar=progressbar
        )
        click.echo(f"Dumped {ndocs} documents and {nfiles} files to {dumpfile}")


@cli.command()
@click.argument("dumpfile", type=click.Path(exists=True))
@click.option(
    "--progressbar/--no-progressbar", default=True, help="Display a progressbar."
)
def undump(dumpfile, progressbar):
    "Load a DataGraphics database dump file. The database must be empty."
    app = datagraphics.config.create_app(__name__)
    with app.app_context():
        utils.set_db()
        if utils.get_count("users", "username") != 0:
            raise click.ClickException(
                f"The database '{app.config['COUCHDB_DBNAME']}' is not empty."
            )
        ndocs, nfiles = flask.g.db.undump(dumpfile, progressbar=progressbar)
        click.echo(f"Loaded {ndocs} documents and {nfiles} files.")

@cli.command()
@click.argument("old_baseurl", type=str)
@click.argument("new_baseurl", type=str)
def baseurl(old_baseurl, new_baseurl):
    "Exchange the base URL of all data sources for all graphics."
    def exchange(data, old_baseurl, new_baseurl):
        if isinstance(data, dict):
            for key, value in list(data.items()):
                if isinstance(value, (dict, list)):
                    exchange(value, old_baseurl, new_baseurl)
                elif key == "url" and value.startswith(old_baseurl):
                    data["url"] = new_baseurl + value[len(old_baseurl):]
                    click.echo(f"{value} -> {data['url']}")
        elif isinstance(data, list):
            for pos, value in enumerate(data):
                if isinstance(value, (dict, list)):
                    exchange(value, old_baseurl, new_baseurl)

    app = datagraphics.config.create_app(__name__)
    with app.app_context():
        utils.set_db()
        view = flask.g.db.view(
            "graphics",
            "owner_modified",
            startkey=("ZZZZZZ", "ZZZZZZ"),
            endkey=("", ""),
            include_docs=True,
            reduce=False,
            descending=True
        )
        for row in view:
            exchange(row.doc, old_baseurl, new_baseurl)
            flask.g.db.put(row.doc)


if __name__ == "__main__":
    cli()
