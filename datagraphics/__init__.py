"Serve data and graphics on the web using Vega-Lite graphics."

import re
import os.path
import string

__version__ = "0.7.8"

class Constants:
    VERSION = __version__
    URL = "https://github.com/pekrau/DataGraphics"
    ROOT_DIRPATH = os.path.dirname(os.path.abspath(__file__))

    # Currently, these are hardwired.
    BOOTSTRAP_VERSION = "4.3.1"
    BOOTSTRAP_URL = "https://getbootstrap.com/"
    JQUERY_VERSION = "3.3.1"
    JQUERY_URL = "https://jquery.com/"
    DATATABLES_VERSION = "1.10.18"
    DATATABLES_URL = "https://datatables.net/"
    VEGA_VERSION = "5.12.1"
    VEGA_URL = "https://vega.github.io/vega/"
    VEGA_LITE_VERSION = "4.12.2"  # Must match schema file in 'static'.
    VEGA_LITE_URL = "https://vega.github.io/vega-lite/"
    VEGA_LITE_SCHEMA_URL = "https://vega.github.io/schema/vega-lite/v4.json"
    VEGA_EMBED_VERSION = "6.8.0"
    VEGA_EMBED_URL = "https://github.com/vega/vega-embed"
    VEGA_LITE_TYPES = ("quantitative", "temporal",
                       "ordinal", "nominal", "geojson")

    IUID_RX = re.compile(r"^[a-f0-9]{32,32}$")
    NAME_RX = re.compile(r"^[a-z][a-z0-9_-]*$", re.I)
    EMAIL_RX = re.compile(r"^[a-z0-9_.+-]+@[a-z0-9-]+\.[a-z0-9-.]+$")
    YEAR_RX = re.compile(r"^[1-9]\d\d\d$", re.ASCII)
    DATE_RX = re.compile(r"^[1-9]\d\d\d-\d\d-\d\d$", re.ASCII)
    DATETIME_RX = re.compile(r"^[1-9]\d\d\d-\d\d-\d\d \d\d:\d\d(:\d\d)?$",
                             re.ASCII)
    TIME_RX = re.compile(r"^\d\d:\d\d(:\d\d)?$", re.ASCII)

    SLUG_CHARS = frozenset(string.ascii_letters + string.digits + "-")

    # CouchDB document types
    DOCTYPE_DATASET = "dataset"
    DOCTYPE_GRAPHIC = "graphic"
    DOCTYPE_USER = "user"
    DOCTYPE_LOG = "log"

    # User roles
    ADMIN = "admin"
    USER  = "user"
    USER_ROLES = (ADMIN, USER)

    # User statuses
    PENDING = "pending"
    ENABLED = "enabled"
    DISABLED = "disabled"
    USER_STATUSES = (PENDING, ENABLED, DISABLED)

    # Content types
    HTML_MIMETYPE = "text/html"
    JSON_MIMETYPE = "application/json"
    CSV_MIMETYPE = "text/csv"
    JS_MIMETYPE = "text/javascript"
    EXCEL_MIMETYPE = "application/vnd.ms-excel"

    # JSON Schema; Draft 7 validator is currently hardwired.
    JSON_SCHEMA_URL = "http://json-schema.org/draft-07/schema#"

    def __setattr__(self, key, value):
        raise ValueError("cannot set constant")


constants = Constants()
