#!/usr/bin/env python
import os
import sys
import time
import shlex
import getpass
import argparse
import requests
import subprocess
from ConfigParser import ConfigParser

from openag_cloud.util import log_in, log_out
from openag_cloud.db_names import global_dbs

def create_admin(db_url, username=None, password=None):
    """
    Creates an admin account with username `username` and password `password`
    on the CouchDB instance at `db_url`. Authenticates as this user and returns
    the cookie generated for the session.
    """
    if not username or not password:
        print "Please define login credentials for the system administrator"
    if not username:
        sys.stdout.write("Username: ")
        username = raw_input()
    if not password:
        password = getpass.getpass("Password: ")
        confirm_password = getpass.getpass("Confirm password: ")
        if confirm_password != password:
            raise RuntimeError("The passwords don't match")

    # Check if the user already exists
    try:
        log_in(db_url, username, password)
    except Exception:
        # If not, create it
        res = requests.put(
            "{}/_config/admins/{}".format(db_url, username),
            data='"{}"'.format(password)
        )
        if not res.status_code == 200:
            raise RuntimeError(
                "Failed to create admin user: {}".format(res.content)
            )
        res = requests.put(
            "{}/_config/couch_https_auth/require_valid_user".format(db_url),
            data='"true"'
        )
        if not res.status_code == 200:
            raise RuntimeError(
                "Failed to enable user authentication: {}".format(res.content)
            )
    return log_in(db_url, username, password)

def write_config(db_url, cookie):
    auth_headers = {"Cookie": cookie}
    config_file_path = os.path.join(os.path.dirname(__file__), "couchdb.ini")
    config = ConfigParser()
    config.read(config_file_path)
    for section in config.sections():
        for param, value in config.items(section):
            url = "{}/_config/{}/{}".format(db_url, section, param)
            current_val = requests.get(url, headers=auth_headers).content.strip()
            desired_val = '"{}"'.format(value.replace('"', '\\"'))
            if current_val != desired_val:
                res = requests.put(url, data=desired_val, headers=auth_headers)
                # Unless there is some delay between requests, CouchDB gets
                # sad. I'm not really sure why
                time.sleep(1)
                if not res.status_code == 200:
                    raise RuntimeError(
                        'Failed to set configuration parameter "{}": {}'.format(
                            param, res.content
                        )
                    )

def create_global_dbs(db_url, cookie):
    auth_headers = {"Cookie": cookie}
    for db_name in global_dbs:
        # Check if the db already exists
        res = requests.get(
            "{}/{}".format(db_url, db_name), headers=auth_headers
        )
        if res.status_code == 200:
            continue
        res = requests.put(
            "{}/{}".format(db_url, db_name), headers=auth_headers
        )
        if not res.status_code == 201:
            raise RuntimeError(
                    'Failed to create database "{}": {}'.format(
                        db_name, res.content
                    )
            )

def main():
    parser = argparse.ArgumentParser(
        description="Initialize the CouchDB server"
    )
    parser.add_argument(
        "-u", "--username", action="store", help="Username of the admin user "
        "to create"
    )
    parser.add_argument(
        "-p", "--password", action="store", help="Password of the admin user "
        "to create"
    )
    parser.add_argument(
        "-D", "--database", action="store", default="http://localhost:5984",
        help='''
Address of the CouchDB instance to initialize. Defaults to
"http://localhost:5984"
        '''
    )
    parser.add_argument
    args = parser.parse_args()
    username, password = args.username, args.password
    cookie = create_admin(args.database, username, password)
    write_config(args.database, cookie)
    create_global_dbs(args.database, cookie)
    log_out(args.database, cookie)

if __name__ == '__main__':
    main()
