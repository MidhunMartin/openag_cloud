import os
import time
import json
import click

@click.group()
def main():
    """ Command Line Interface for OpenAg Cloud """
    pass

@main.command()
@click.argument("db_url", default="http://localhost:5984")
@click.argument("api_url", default="http://localhost:5000")
@click.option("--username", prompt=True)
@click.option(
    "--password", prompt=True, hide_input=True, confirmation_prompt=True
)
def init(db_url, api_url, username, password):
    """ Initialize the CouchDB server """
    from .util import CouchSession
    from .db_names import global_dbs
    from .db_config import generate_config
    import requests

    s = CouchSession(db_url)

    # Create the admin user if it doesn't already exist
    try:
        s.log_in(username, password)
    except Exception: # The admin user doesn't exists yet
        res = s.put(
            "_config/admins/{}".format(username), data='"{}"'.format(password)
        )
        if not res.status_code == 200:
            raise RuntimeError("Failed to create admin user: " + res.content)
        res = s.put(
            "_config/couch_https_auth/require_valid_user", data='"true"'
        )
        if not res.status_code == 200:
            raise RuntimeError(
                "Failed to enforce user authentication: " + res.content
            )
        s.log_in(username, password)

    # Apply the database configuration
    db_config = generate_config(api_url=api_url)
    for section, values in db_config.items():
        for param, value in values.items():
            url = "_config/{}/{}".format(section, param)
            current_val = s.get(url).content.strip()
            desired_val = '"{}"'.format(value.replace('"', '\\"'))
            if current_val != desired_val:
                res = s.put(url, data=desired_val)
                # Unless there is some delay between requests, CouchDB gets sad
                # for some reason
                time.sleep(1)
                if not res.status_code == 200:
                    s.log_out()
                    raise RuntimeError(
                        'Failed to set configuration parameter "{}": {}'.format(
                            param, res.content
                        )
                    )

    # Create all global dbs on the server
    for db_name in global_dbs:
        # Check if the db already exists
        res = s.get(db_name)
        if res.status_code != 200:
            # Create the database
            res = s.put(db_name)
            if not res.status_code == 201:
                raise RuntimeError(
                        'Failed to create database "{}": {}'.format(
                            db_name, res.content
                        )
                )

        # Write a design document to the database to make it read-only
        url = "{}/_design/openag".format(db_name)
        # Construct the new design doc
        new_design_doc = {"_id": "_design/openag"}
        here = os.path.dirname(os.path.abspath(__file__))
        file_name = os.path.join(here, "validate_doc_update.js")
        with open(file_name, "r") as f:
            new_design_doc["validate_doc_update"] = f.read()
        # Check if there is an existing design doc
        old_design_doc = {}
        rev = None
        res = s.get(url)
        if res.status_code == 200:
            old_design_doc = json.loads(res.content)
            rev = old_design_doc.pop("_rev")
        # If they are different, update the design doc
        if set(new_design_doc.items()) ^ set(old_design_doc.items()):
            if rev:
                new_design_doc["_rev"] = rev
            res = s.put(url, data=json.dumps(new_design_doc))
            if res.status_code != 201:
                raise RuntimeError(
                    'Failed to write design document to database "{}": {}'.format(
                        db_name, res.content
                    )
                )

    s.log_out()

@main.command()
@click.argument("secret_key")
@click.argument("db_url", default="http://localhost:5984")
@click.option("--username", prompt=True)
@click.option("--password", prompt=True, hide_input=True
)
def api(secret_key, db_url, username, password):
    """ Runs the cloud API for registering farms """
    from .api import create_app
    from gevent.wsgi import WSGIServer
    app = create_app(db_url, username, password, secret_key)
    http_server = WSGIServer(("", 5000), app)
    http_server.serve_forever()
