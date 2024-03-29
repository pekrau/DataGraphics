"Configuration."

import json
import os
import os.path

import flask
from werkzeug.middleware.proxy_fix import ProxyFix

import datagraphics.dataset
import datagraphics.graphic
import datagraphics.user

from datagraphics import constants
from datagraphics import utils


# Default configurable values; modified by reading a JSON file in 'init'.
DEFAULT_SETTINGS = dict(
    SERVER_NAME=None,
    REVERSE_PROXY=False,
    SITE_STATIC_DIR=os.path.normpath(os.path.join(constants.ROOT, "../site/static")),
    LOG_DEBUG=False,
    LOG_NAME="datagraphics",
    LOG_FILEPATH=None,
    LOG_ROTATING=0,  # Number of backup rotated log files, if any.
    LOG_FORMAT="%(levelname)-10s %(asctime)s %(message)s",
    CONTACT_EMAIL=None,
    SECRET_KEY=None,  # Must be set in 'settings.json'.
    SALT_LENGTH=12,
    COUCHDB_URL="http://127.0.0.1:5984/",
    COUCHDB_USERNAME=None,
    COUCHDB_PASSWORD=None,
    COUCHDB_DBNAME="datagraphics",
    JSON_AS_ASCII=False,
    JSON_SORT_KEYS=False,
    JSONIFY_PRETTYPRINT_REGULAR=False,
    MAX_RECORDS_INSPECT=2000,
    MIN_PASSWORD_LENGTH=6,
    PERMANENT_SESSION_LIFETIME=7 * 24 * 60 * 60,  # in seconds: 1 week
    MAX_HOME_LIST_ITEMS=10,
    URL_UPDATE_TIMEOUT=5.0,
    MAIL_SERVER=None,  # e.g. "localhost", if set up.
    MAIL_PORT=25,
    MAIL_USE_TLS=False,
    MAIL_USERNAME=None,
    MAIL_PASSWORD=None,
    MAIL_DEFAULT_SENDER=None,
    USER_REGISTER=True,
    USER_ENABLE_IMMEDIATELY=False,
    USER_ENABLE_EMAIL_WHITELIST=[],  # List of regexp's
    MARKDOWN_URL="https://www.markdownguide.org/basic-syntax/",
)


def create_app(name, init_db=True):
    "Create the Flask app instance and do the main configuration."
    # The reason this is defined here, and not in 'main.py', is that the
    # standalone 'cli.py' must also use it. There is further initialization
    # done at the module level in 'main.py', which must not be done when this
    # function is called from 'cli.py'. Therefore, the module 'datagraphics.main'
    # cannot be imported by 'cli.py'.
    app = flask.Flask(name)
    init(app)
    if init_db:
        utils.init(app)
        utils.mail.init_app(app)
        load_db_designs(app)
    return app

def init(app):
    """Perform the configuration of the Flask app.
    Set the defaults, and then modify the values based on:
    1) The settings file path environment variable DATAGRAPHICS_SETTINGS_FILEPATH.
    2) The file 'settings.json' in this directory.
    3) The file '../site/settings.json' relative to this directory.
    Check the environment for variables and use if defined.
    Raise IOError if settings file could not be read.
    Raise KeyError if a settings variable is missing.
    Raise ValueError if a settings variable value is invalid.
    Check the environment for a specific set of variables and use if defined.
    """
    # Set the defaults specified above.
    app.config.from_mapping(DEFAULT_SETTINGS)

    # Modify the configuration from a JSON settings file.
    try:
        filepaths = [os.environ["DATAGRAPHICS_SETTINGS_FILEPATH"]]
    except KeyError:
        filepaths = []
    for filepath in ["settings.json", "../site/settings.json"]:
        filepaths.append(os.path.normpath(os.path.join(constants.ROOT, filepath)))
    for filepath in filepaths:
        try:
            app.config.from_file(filepath, load=json.load)
        except FileNotFoundError:
            pass
        else:
            app.config["SETTINGS_FILE"] = filepath
            break

    # Modify the configuration from environment variables.
    for key, value in DEFAULT_SETTINGS.items():
        try:
            new = os.environ[key]
        except KeyError:
            pass
        else:  # Do NOT catch any exception! Means bad setup.
            if isinstance(value, int):
                app.config[key] = int(new)
            elif isinstance(value, bool):
                app.config[key] = bool(new)
            else:
                app.config[key] = new

    # Sanity check; should not execute if this fails.
    if not app.config["SECRET_KEY"]:
        raise ValueError("SECRET_KEY not set")
    if app.config["SALT_LENGTH"] <= 6:
        raise ValueError("SALT_LENGTH is too short")
    if app.config["MIN_PASSWORD_LENGTH"] <= 4:
        raise ValueError("MIN_PASSWORD_LENGTH is too short")

    if app.config["REVERSE_PROXY"]:
        app.wsgi_app = ProxyFix(app.wsgi_app)

    # Read and preprocess the documentation file.
    with open("documentation.md") as infile:
        lines = infile.readlines()
    toc = []
    current_level = 0
    for line in lines:
        if line.startswith("#"):
            parts = line.split()
            level = len(parts[0])
            title = " ".join(parts[1:])
            # All headers in the file are "clean", i.e. text only, no markup.
            id = title.strip().replace(" ", "-").lower()
            id = "".join(c for c in id if c in constants.ALLOWED_ID_CHARACTERS)
            # Add to table of contents.
            if level <= 2:
                if level > current_level:
                    for l in range(current_level, level):
                        toc.append('<ul class="list-unstyled ml-3">')
                    current_level = level
                elif level < current_level:
                    for l in range(level, current_level):
                        toc.append("</ul>")
                    current_level = level
                toc.append(f'<li><a href="#{id}">{title}</a></li>')
    for level in range(current_level):
        toc.append("</ul>")
    app.config["DOCUMENTATION_TOC"] = "\n".join(toc)
    app.config["DOCUMENTATION"] = utils.markdown2html("".join(lines))

    # Read in JSON Schema for Vega-Lite from file in 'static'.
    filepath = os.path.join(
        constants.ROOT, f"static/v{constants.VEGA_LITE_VERSION}.json"
    )
    with open(filepath) as infile:
        app.config["VEGA_LITE_SCHEMA"] = json.load(infile)

    # Read in stencil JSON specifications from files in 'stencils'.
    app.config["STENCILS"] = {}
    for rootpath in ["stencils", "../site/stencils"]:
        rootpath = os.path.normpath(os.path.join(constants.ROOT, rootpath))
        if not os.path.exists(rootpath) or not os.path.isdir(rootpath):
            continue
        for filename in os.listdir(rootpath):
            name, ext = os.path.splitext(filename)
            if ext != ".json":
                continue
            with open(os.path.join(rootpath, filename)) as infile:
                stencil = json.load(infile)
                stencil["header"]["name"] = name
                for variable in stencil["header"]["variables"]:
                    variable["name"] = "/".join(variable["path"])
                app.config["STENCILS"][name] = stencil


def load_db_designs(app):
    "Load the design documents."
    datagraphics.dataset.init(app)
    datagraphics.graphic.init(app)
    datagraphics.user.init(app)
