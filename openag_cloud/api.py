#!/usr/bin/env python
import json
import argparse
import requests
from flask import Flask, request, jsonify
from urllib import quote

from db_names import per_user_dbs

API_VER = "0.0.1"

app = Flask(__name__)

admin_username = None
admin_password = None

@app.route("/api/{v}/register_user".format(v=API_VER), methods=["POST"])
def register_user():
    if not "username" in request.values:
        return jsonify({"error": "No username was supplied"}), 400
    if not "password" in request.values:
        return jsonify({"error": "No password was supplied"}), 400
    username = request.values["username"]
    password = request.values["password"]
    user_id = "org.couchdb.user:{}".format(username)
    res = requests.put(
        "http://localhost:5984/_users/{}".format(user_id),
        data=json.dumps({
            "_id": user_id,
            "name": username,
            "password": password,
            "roles": [],
            "type": "user"
        })
    )
    if res.status_code == 409:
        return jsonify(
            {"error": "A user with that username already exists"}
        ), 409
    if res.status_code == 200:
        return res.content, 200
    return res.content, res.status_code

@app.route("/api/{v}/register_farm".format(v=API_VER), methods=["POST"])
def register_farm():
    # Validate and extract supplied parameters
    if not "username" in request.values:
        return jsonify({"error": "No username was supplied"}), 400
    if not "password" in request.values:
        return jsonify({"error": "No password was supplied"}), 400
    if not "farm_name" in request.values:
        return jsonify({"error": "No farm_name was supplied"}), 400
    username = request.values["username"]
    password = request.values["password"]
    farm_name = request.values["farm_name"]

    # Make sure the user exists and the credentials are correct
    user_info = requests.get(
        "http://{u}:{p}@localhost:5984/_users/org.couchdb.user:{u}".format(
            u=username, p=password
        )
    ).json()

    # Create and configure datbases to store the farm data
    full_db_names = {
        db_name: quote("{}/{}/{}".format(username, farm_name, db_name), "")
        for db_name in per_user_dbs
    }
    for full_db_name in full_db_names.values():
        # Create the database
        res = requests.put(
            "http://{u}:{p}@localhost:5984/{db_name}".format(
                u=admin_username, p=admin_password, db_name=full_db_name
            )
        )
        if not res.status_code in [201, 412]:
            return jsonify({
                "error": "Failed to create database {}".format(full_db_name)
            })

        # Write security docs for the databases
        res = requests.put(
            "http://{u}:{p}@localhost:5984/{db_name}/_security".format(
                u=admin_username, p=admin_password, db_name=full_db_name
            ), data=json.dumps({
                "admins": {
                    "names": [],
                    "roles": []
                },
                "members": {
                    "names": [username],
                    "roles": []
                }
            })
        )
        # If this fails, delete the database and give up
        if not res.status_code == 200:
            res = requests.delete(
                "http://{u}:{p}@localhost:5984/{db_name}".format(
                    u=admin_username, p=admin_password, db_name=full_db_name
                )
            )
            return jsonify({
                "error": "Failed to set security information for the database"
            }), 400
    return jsonify(full_db_names)

def main():
    parser = argparse.ArgumentParser(
        description="""
Runs the server responsible for creating new users and creating database for
them to replicate into.
""")
    parser.add_argument("admin_username")
    parser.add_argument("admin_password")
    args = parser.parse_args()
    global username, password
    admin_username = args.admin_username
    admin_password = args.admin_password
    from gevent.wsgi import WSGIServer
    http_server = WSGIServer(("", 5000), app)
    http_server.serve_forever()

if __name__ == '__main__':
    main()
