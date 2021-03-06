def generate_config(api_url):
    return  {
        "httpd": {
            "port": "5984",
            "bind_address": "0.0.0.0",
            "enable_cors": "true",
            "WWW-Authenticate": "Basic realm=\"administrator\"",
        },
        "cors": {
            "origins": "*",
            "credentials": "true",
        },
        "httpd_global_handlers": {
            "_openag": "{{couch_httpd_proxy, handle_proxy_req, <<\"{}\">>}}".format(api_url)
        }
    }
