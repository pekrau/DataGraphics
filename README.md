# ![DataGraphics logo](https://github.com/pekrau/DataGraphics/raw/master/datagraphics/static/logo32.png) DataGraphics

Datasets and graphics served on the web using Vega-Lite.

Uses Python3, Flask, Vega-Lite, CouchDB server, CouchDB2 (Python module),
Marko, emoji, jsonschema, Bootstrap, jQuery, DataTables.

[Vega-Lite](https://vega.github.io/vega-lite/)
is a JavaScript library implementing a grammar of interactive graphics,
provided by the
[University of Washington Interactive Data Lab](https://idl.cs.washington.edu/)
(UW IDL).

## API usage

For an example of how to use the API to update dataset contents, see
[example_dataset_update.py](https://github.com/pekrau/DataGraphics/blob/master/datagraphics/api/example_dataset_update.py)

## Installation

1. Download and unpack the zipped codebase from
   [https://github.com/pekrau/DataGraphics](https://github.com/pekrau/DataGraphics).
   The source code directory is called `{SOURCE}` in the following.

2. Set up your Python3 environment, e.g. using virtualenv, for the
   `{SOURCE}` directory.

3. Install the required Python3 third-party packages (Flask, etc) using
   `pip install -r requirements.txt'` in the `{SOURCE}` directory.
   
4. Create your JSON file `settings.json` in either the directory
   `{SOURCE}/site` or `{SOURCE}/datagraphics` by making a copy of 
   `{SOURCE}/site/settings_template.json`. Edit as appropriate for your site.

   For security, the `settings.json` should be readable only for the Linux
   account that runs the Flask server process.

   The `settings.json` file may contain an entry `ADMIN_USER` which will
   create an admin user if it doesn't exist. See the `settings_template.json`
   file for how it should look. The password for this user ought to be
   changed as soon as it has been created, for security.
   
   If your email server is not the simple `localhost` with no password,
   then you need to set those variables. See the file
   `{SOURCE}/datagraphics/config.py` for all email-related settings
   variables.

5. Set up the CouchDB database that your app will use, and add the name of
   it, any required username and password for it, in your `settings.json`
   file.

6. Include the `{SOURCE}` directory in the Python path. This can be done
   in different ways. The simplest is to set it in the shell
   (e.g. in your .bashrc file):
   ```
   $ cd {SOURCE}
   $ export PYTHONPATH=$PWD:$PYTHONPATH
   ```

7. You mays use the command-line interface to create user accounts.
   (See point 4 above for how to create an admin user in a different way.)
   This will also automatically load the index definitions to
   the CouchDB server, if not already done.
   ```
   $ python cli.py -A
   ```

8. Run the Flask app in development mode as usual. This will automatically
   load the index definitons to the CouchDB server, if not already done.
   If the `ADMIN_USER` entry has been defined properly in the `settings.json`
   file, it will be created.
   ```
   $ python app.py
   ```

9. For running the Flask app in production mode, see the information
   in the Flask manual and/or the Apache, nginx, or whichever
   outward-facing web server you are using.


## Development environment

`docker-compose`, `curl`, and `sed` are needed.

1. Create a settings file: `cp site/settings_template.json datagraphics/settings.json`
2. Change the host to `db`: `sed -i 's/127.0.0.1:5984/db:5984/' datagraphics/settings.json`
3. Start the database: `docker-compose up db`
4. Create the database `datagraphics`: `curl -u 'couchdb_db_account:couchdb_db_account_pwd' -X PUT http://localhost:5984/datagraphics`
5. Stop the database: `ctrl-c` or `docker-compose stop`
6. Start the full system: `docker-compose up`

The development system can be accessed at: [http://127.0.0.1:5005/](http://127.0.0.1:5005/)

Port numbers on localhost can be changed in `docker-compose.yml`, e.g.:
```
    ports:
      - 127.0.0.1:5000:5005
```
will allow you to access port 5005 in the container at port 5000 on localhost (127.0.0.1).
