#!/usr/bin/env python
import json
import requests
from flask import Flask, request, jsonify, render_template, current_app
from flask_wtf import Form
from wtforms import StringField
from wtforms.validators import Required
from urllib import quote

from .util import CouchSession
from .db_names import per_farm_dbs

API_VER = "v0.1"

class FarmForm(Form):
    name = StringField(validators=[Required()])
    farm_name = StringField(validators=[Required()])

def create_app(db_url, admin_username, admin_password, secret_key):
    app = Flask(__name__)

    app.config["SECRET_KEY"] = secret_key

    app.s = CouchSession(db_url)
    app.s.log_in(admin_username, admin_password)

    @app.route("/{v}/register_farm".format(v=API_VER), methods=["POST"])
    def register_farm():
        form = FarmForm(csrf_enabled=False)
        if not form.validate_on_submit():
            return json.dumps(form.errors), 400
        if not "Cookie" in request.headers:
            return jsonify({"error": "Anonymous users cannot register farms"}), 403

        # Make sure the cookie is for the correct user
        res = current_app.s.get(
            "_session", headers={"Cookie": request.headers["Cookie"]}
        ).json()
        if res["userCtx"]["name"] is None:
            return jsonify({"error": "Session expired"}), 400
        if not res["userCtx"]["name"] == form.name.data:
            return jsonify({
                "error": "Provided username does not match current user"
            }), 400

        # Create and configure datbases to store the farm data
        full_db_names = {
            db_name: "{}/{}/{}".format(
                form.name.data, form.farm_name.data, db_name
            ) for db_name in per_farm_dbs
        }
        for full_db_name in full_db_names.values():
            # Create the database
            res = current_app.s.put(quote(full_db_name, ""))
            if not res.status_code in [201, 412]:
                return jsonify({
                    "error": "Failed to create database {}".format(full_db_name)
                })

            # Write security docs for the databases
            res = current_app.s.put(
                quote(full_db_name, "") + "/_security",
                data=json.dumps({
                    "admins": {
                        "names": [],
                        "roles": []
                    },
                    "members": {
                        "names": [form.name.data],
                        "roles": []
                    }
                })
            )
            # If this fails, delete the database and give up
            if not res.status_code == 200:
                res = current_app.s.delete(quote(full_db_name, ""))
                return jsonify({
                    "error": "Failed to set security information for the database"
                }), 400

        # Update the user object to reflect the new farm
        user_url = quote("_users/org.couchdb.user:")+form.name.data
        user_info = current_app.s.get(user_url).json()
        if not "farms" in user_info:
            user_info["farms"] = []
        farms = set(user_info["farms"])
        farms.add(form.farm_name.data)
        user_info["farms"] = list(farms)
        res = current_app.s.put(user_url, data=json.dumps(user_info))
        if not res.status_code == 200:
            return "Failed to update user info" + res.content, res.status_code
        return jsonify(full_db_names)
    return app
