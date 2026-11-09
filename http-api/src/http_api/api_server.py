# Simple HTTP RESTful API Server. From the http-api folder run: uv run http-api-server
# In the container the same command is the CMD of the Docker image.

import signal
import sys
from types import FrameType
from typing import Any

from flask import Flask
from flask_restful import Api
from werkzeug.serving import make_server

from http_api.config.config_loader import ConfigLoader
from http_api.resources.test_resource import TestResource

# Configuration file (searched in the working directory and in the project root)
CONF_FILE_PATH = "conf.yaml"

# Default configuration, used for the parameters not defined in the configuration file
DEFAULT_CONFIGURATION: dict[str, Any] = {
    "rest": {
        "api_prefix": "/api/iot",
        "host": "0.0.0.0",
        "port": 7070
    }
}


def handle_sigterm(signum: int, frame: FrameType | None) -> None:
    """ Stop the server when the container is stopped (docker stop sends SIGTERM to the main process) """
    sys.exit(0)


def main() -> None:

    # Read the configuration file
    configuration = ConfigLoader.load(CONF_FILE_PATH, DEFAULT_CONFIGURATION)
    rest_configuration = configuration["rest"]

    # Create the Flask application and the RESTful API with the test resource
    app = Flask(__name__)
    api = Api(app)
    api.add_resource(TestResource, rest_configuration['api_prefix'] + '/test',
                     endpoint="TestEndPoint",
                     methods=['GET'])

    # In a container the process has PID 1 and ignores SIGTERM unless a handler is installed
    signal.signal(signal.SIGTERM, handle_sigterm)

    print("Starting HTTP RESTful API Server ...")
    http_server = make_server(rest_configuration['host'], rest_configuration['port'], app, threaded=True)
    print(f"HTTP RESTful API Server running on http://{rest_configuration['host']}:{rest_configuration['port']}"
          f"{rest_configuration['api_prefix']}/test")

    try:
        http_server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        print("HTTP RESTful API Server stopped")
    finally:
        http_server.server_close()


if __name__ == "__main__":
    main()
