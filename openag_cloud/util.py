import requests

def log_in(db_url, username, password):
    """
    Logs in to the CouchDB instance given by `db_url` with the credentials
    `username` and `password` and returns the cookie associated with the new
    session.
    """
    res = requests.post(
        "{}/_session".format(db_url),
        data={"name": username, "password": password}
    )
    if not res.status_code == 200:
        raise RuntimeError(
            "Failed to login to CouchDB: " + res.content
        )
    return res.headers["Set-Cookie"].split(';')[0]

def log_out(db_url, cookie):
    """
    Logs out of the session defined by the cookie `cookie` on the CouchDB
    instance given by `db_url`
    """
    res = requests.delete("{}/_session".format(db_url))
    if res.status_code != 200:
        raise RuntimeError(
            "Failed to log out of CouchDB: " + res.content
        )

