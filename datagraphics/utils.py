"Various utility functions and classes."

import datetime
import functools
import http.client
import json
import logging
import time
import unicodedata
import uuid

import couchdb2
import emoji
import flask
import flask_mail
import jsonschema
import marko
import markupsafe
import werkzeug.routing

from datagraphics import constants


def init(app):
    """Initialize app.
    - Add URL map converters.
    - Add template filters.
    - Update CouchDB design document.
    """
    app.url_map.converters["name"] = NameConverter
    app.url_map.converters["iuid"] = IuidConverter
    app.add_template_filter(tojson_noescape)
    app.add_template_filter(markdown2html)
    app.add_template_filter(emojize)
    app.add_template_filter(float_default)
    db = get_db(app=app)
    logger = get_logger(app)
    if db.put_design("logs", DESIGN_DOC):
        logger.info("Updated logs design document.")


DESIGN_DOC = {
    "views": {
        "doc": {
            "map": "function(doc) {if (doc.doctype !== 'log') return; emit([doc.docid, doc.timestamp], null);}"
        }
    },
}

# Global logger instance.
_logger = None


def get_logger(app=None):
    global _logger
    if _logger is None:
        if app is None:
            config = flask.current_app.config
        else:
            config = app.config
        _logger = logging.getLogger(config["LOG_NAME"])
        if config["LOG_DEBUG"]:
            _logger.setLevel(logging.DEBUG)
        else:
            _logger.setLevel(logging.WARNING)
        if config["LOG_FILEPATH"]:
            if config["LOG_ROTATING"]:
                loghandler = logging.TimedRotatingFileHandler(
                    config["LOG_FILEPATH"],
                    when="midnight",
                    backupCount=config["LOG_ROTATING"],
                )
            else:
                loghandler = logging.FileHandler(config["LOG_FILEPATH"])
        else:
            loghandler = logging.StreamHandler()
        loghandler.setFormatter(logging.Formatter(config["LOG_FORMAT"]))
        _logger.addHandler(loghandler)
    return _logger


def set_db(app=None):
    "Sets the database connection and creates the document cache."
    flask.g.db = get_db(app=app)


def get_db(app=None):
    if app is None:
        app = flask.current_app
    return get_server(app=app)[app.config["COUCHDB_DBNAME"]]


def get_server(app=None):
    if app is None:
        app = flask.current_app
    return couchdb2.Server(
        href=app.config["COUCHDB_URL"],
        username=app.config["COUCHDB_USERNAME"],
        password=app.config["COUCHDB_PASSWORD"],
    )
    

def get_count(designname, viewname, key=None):
    "Get the count for the given view and key."
    if key is None:
        result = flask.g.db.view(designname, viewname, reduce=True)
    else:
        result = flask.g.db.view(designname, viewname, key=key, reduce=True)
    if result:
        return result[0].value
    else:
        return 0


def get_logs(docid, cleanup=True):
    """Return the list of log entries for the given document identifier,
    sorted by reverse timestamp.
    """
    result = [
        r.doc
        for r in flask.g.db.view(
            "logs",
            "doc",
            startkey=[docid, "ZZZZZZ"],
            endkey=[docid],
            descending=True,
            include_docs=True,
        )
    ]
    if cleanup:
        for log in result:
            for key in ["_id", "_rev", "doctype", "docid"]:
                log.pop(key)
    return result


def log_access(response):
    "Record access using the logger."
    if flask.g.current_user:
        username = flask.g.current_user["username"]
    else:
        username = None
    get_logger().debug(
        f"{flask.request.remote_addr} {username}"
        f" {flask.request.method} {flask.request.path}"
        f" {response.status_code}"
    )
    return response


# Global instance of mail interface.
mail = flask_mail.Mail()

# Decorators for endpoints
def login_required(f):
    "Decorator for checking if logged in. Send to login page if not."

    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not flask.g.current_user:
            flask.session["login_target_url"] = flask.request.base_url
            return flask.redirect(flask.url_for("user.login"))
        return f(*args, **kwargs)

    return wrap


def admin_required(f):
    """Decorator for checking if logged in and 'admin' role.
    Otherwise return status 401 Unauthorized.
    """

    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not flask.g.am_admin:
            flask.abort(http.client.UNAUTHORIZED)
        return f(*args, **kwargs)

    return wrap


class NameConverter(werkzeug.routing.BaseConverter):
    "URL route converter for a name."

    def to_python(self, value):
        if not constants.NAME_RX.match(value):
            raise werkzeug.routing.ValidationError
        return value.lower()  # Case-insensitive


class IuidConverter(werkzeug.routing.BaseConverter):
    "URL route converter for a IUID."

    def to_python(self, value):
        if not constants.IUID_RX.match(value):
            raise werkzeug.routing.ValidationError
        return value.lower()  # Case-insensitive


class Timer:
    "CPU timer."

    def __init__(self):
        self.start = time.perf_counter()

    def __call__(self):
        "Return CPU time (in seconds) since start of this timer."
        return time.perf_counter() - self.start

    @property
    def milliseconds(self):
        "Return CPU time (in milliseconds) since start of this timer."
        return round(1000 * self())


def get_iuid():
    "Return a new IUID, which is a UUID4 pseudo-random string."
    return uuid.uuid4().hex


def to_bool(s):
    "Convert string value into boolean."
    if not s:
        return False
    s = s.lower()
    return s in ("true", "t", "yes", "y")


def get_time(offset=None):
    """Current date and time (UTC) in ISO format, with millisecond precision.
    Add the specified offset in seconds, if given.
    """
    instant = datetime.datetime.utcnow()
    if offset:
        instant += datetime.timedelta(seconds=offset)
    instant = instant.isoformat()
    return instant[:17] + "{:06.3f}".format(float(instant[17:])) + "Z"


def url_referrer(url=None):
    """Return the URL for the referring page ('referer').
    Return the given URL if no referring page; the home page if none given.
    """
    return flask.request.headers.get("referer") or url or flask.url_for("home")


def http_GET():
    "Is the HTTP method GET?"
    return flask.request.method == "GET"


def http_POST(csrf=True):
    "Is the HTTP method POST? Check whether used for method tunneling."
    if flask.request.method != "POST":
        return False
    if flask.request.form.get("_http_method") in (None, "POST"):
        if csrf:
            check_csrf_token()
        return True
    else:
        return False


def http_PUT():
    "Is the HTTP method PUT? Is not tunneled."
    return flask.request.method == "PUT"


def http_DELETE(csrf=True):
    "Is the HTTP method DELETE? Check for method tunneling."
    if flask.request.method == "DELETE":
        return True
    if flask.request.method == "POST":
        if csrf:
            check_csrf_token()
        return flask.request.form.get("_http_method") == "DELETE"
    else:
        return False


def csrf_token():
    "Output HTML for cross-site request forgery (CSRF) protection."
    # Generate a token to last the session's lifetime.
    if "_csrf_token" not in flask.session:
        flask.session["_csrf_token"] = get_iuid()
    html = (
        '<input type="hidden" name="_csrf_token" value="%s">'
        % flask.session["_csrf_token"]
    )
    return markupsafe.Markup(html)


def check_csrf_token():
    "Check the CSRF token for POST HTML."
    # Do not use up the token; keep it for the session's lifetime.
    token = flask.session.get("_csrf_token", None)
    if not token or token != flask.request.form.get("_csrf_token"):
        flask.abort(http.client.BAD_REQUEST)


def flash_error(msg):
    "Flash error message."
    flask.flash(str(msg), "error")


def flash_warning(msg):
    "Flash warning message."
    flask.flash(str(msg), "warning")


def flash_message(msg):
    "Flash information message."
    flask.flash(str(msg), "message")


def tojson_noescape(value, indent=None):
    "Return stringified JSON without escaping any characters."
    return json.dumps(value, indent=indent, ensure_ascii=False)


def markdown2html(value):
    "Process the value from Markdown to HTML."
    return marko.Markdown(renderer=HtmlRenderer).convert(value or "")


class HtmlRenderer(marko.html_renderer.HTMLRenderer):
    "Extension of Marko Markdown-to-HTML renderer."

    def render_link(self, element):
        """Allow setting <a> attribute '_target' to '_blank', when the title
        begins with an exclamation point '!'.
        """
        if element.title and element.title.startswith("!"):
            template = '<a target="_blank" href="{url}"{title}>{body}</a>'
            element.title = element.title[1:]
        else:
            template = '<a href="{url}"{title}>{body}</a>'
        title = (
            ' title="{}"'.format(self.escape_html(element.title))
            if element.title
            else ""
        )
        return template.format(
            url=self.escape_url(element.dest),
            title=title,
            body=self.render_children(element),
        )

    def render_heading(self, element):
        "Add id to all headings."
        id = self.get_text_only(element).replace(" ", "-").lower()
        id = "".join(c for c in id if c in constants.ALLOWED_ID_CHARACTERS)
        return '<h{level} id="{id}">{children}</h{level}>\n'.format(
            level=element.level, id=id, children=self.render_children(element)
        )

    def get_text_only(self, element):
        "Helper function to extract only the text from element and its children."
        if isinstance(element.children, str):
            return element.children
        else:
            return "".join([self.get_text_only(el) for el in element.children])


def emojize(value):
    "Template filter: Convert emoji shortcodes to character."
    return markupsafe.Markup(emoji.emojize(value or "", use_aliases=True))


def float_default(value, default=""):
    if value is None:
        return default
    elif isinstance(value, int):
        return str(value)
    elif isinstance(value, str):
        return value or default
    else:
        return "%g" % value


def slugify(s, lowercase=False):
    """Return the string converted into a valid slug.
    - Lower case, if specified.
    - Dash instead of whitespaces.
    - ASCII letters, numbers and dash.
    - All other characters removed.
    """
    if lowercase:
        s = s.lower()
    s = s.strip()
    s = s.replace(" ", "-")
    s = unicodedata.normalize("NFKD", s)
    return "".join([c for c in s if c in constants.SLUG_CHARS])


def validate_vega_lite(spec):
    """Validate the given spec as proper Vega-Lite.
    Raises 'jsonschema.ValidationError' if something is wrong.
    """
    jsonschema.validate(
        spec,
        flask.current_app.config["VEGA_LITE_SCHEMA"],
        format_checker=jsonschema.draft7_format_checker,
    )


def accept_json():
    "Return True if the header Accept contains the JSON content type."
    acc = flask.request.accept_mimetypes
    best = acc.best_match([constants.JSON_MIMETYPE, constants.HTML_MIMETYPE])
    return best == constants.JSON_MIMETYPE and acc[best] > acc[constants.HTML_MIMETYPE]


def jsonify(data, id=None, timestamp=True, schema=None):
    """Return a Response object containing the JSON of 'data'.
    Fix up the JSON structure for external representation.
    Optionally add a header Link to the schema given by its URL.
    """
    result = {"$id": flask.request.url}
    try:
        result["$schema"] = data.pop("$schema")
    except KeyError:
        pass
    if timestamp:
        result["timestamp"] = get_time()
    try:
        result["iuid"] = data.pop("_id")
    except KeyError:
        pass
    result.update(data)
    result.pop("_rev", None)
    result.pop("doctype", None)
    response = flask.jsonify(result)
    if schema:
        response.headers.add("Link", schema, rel="schema")
    return response


class JsonTraverser:
    "Traverse the JSON data structure, and handle each path/value pair."

    replace = False

    def traverse(self, data):
        self.path = []
        self._traverse(data)

    def _traverse(self, fragment):
        if isinstance(fragment, dict):
            self.path.append(None)
            for key, value in fragment.items():
                self.path[-1] = key
                new = self._traverse(value)
                if self.replace:
                    fragment[key] = new
            self.path.pop()
            return fragment
        elif isinstance(fragment, list):
            self.path.append(None)
            for pos, value in enumerate(fragment):
                self.path[-1] = pos
                new = self._traverse(value)
                if self.replace:
                    fragment[pos] = new
            self.path.pop()
            return fragment
        else:
            return self.handle(fragment)

    def handle(self, value):
        "Handle the current path/value. Optionally return replacement value."
        raise NotImplementedError
