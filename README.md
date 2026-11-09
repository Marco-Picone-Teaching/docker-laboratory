# Docker Laboratory

This Laboratory has the objective to provide a simple step-by-step guide to learn
how to build a simple IoT application using Docker containers exposing a HTTP RESTful API with a single endpoint that returns a JSON response.

The implementation is based on the following Python Frameworks

- Flask: https://flask.palletsprojects.com/
- Flask RESTful: https://flask-restful.readthedocs.io/en/latest/index.html

The Python project is managed with [uv](https://docs.astral.sh/uv/), that is also used inside the container to install
the application and its dependencies.

APIs are exposed through a configurable port (7070) and accessible locally at: [http://127.0.0.1:7070/api/iot/test](http://127.0.0.1:7070/api/iot/test)

Main characteristics of the application are:

- **API Endpoint**: `/api/iot/test`
- **HTTP Method**: `GET`
- **Response**: JSON object with a test message
- **Configuration File**: `conf.yaml` with the API configuration with binding host and port, and the API base path

To simplify the building and the structure of the container the application has been organized with the following structure:

```
http-api/
├── pyproject.toml          # Project metadata, dependencies and the command that starts the server
├── uv.lock                 # Locked versions of all the dependencies
├── .python-version         # Python version of the project (3.12)
├── conf.yaml               # Default configuration of the API server
├── test_conf.yaml          # Alternative configuration, passed to the container at runtime
├── Dockerfile              # Instructions to build the Docker image
├── .dockerignore           # Files excluded from the build context
├── requirements.txt        # Generated from uv.lock for pip-based workflows
└── src/http_api/           # Python package of the application
    ├── api_server.py       # Entry point of the API server
    ├── config/             # ConfigLoader (reads conf.yaml)
    └── resources/          # API resources (TestResource)
```

- **src/http_api**: Contains the Python application files, with a clear separation between the application and the Docker configuration.
- **pyproject.toml** and **uv.lock**: Contain the Python dependencies required by the application and their exact versions.
- **Dockerfile**: Contains the instructions to build the Docker image for the application.
- **conf.yaml**: Contains the configuration of the API server with the binding host and port, and the API base path.
This file is copied to the container and used by the application to read the default configuration.
A new configuration can be passed to the container using a volume at runtime (as we will see later).

In this laboratory we start from the assumption that Docker is already installed on the host machine and that the Docker daemon is running.
Furthermore, we assume that the Docker CLI is available and that the user has the necessary permissions to run Docker commands.
From a knowledge perspective, we assume that the user has a basic understanding of:

- HTTP RESTful APIs
- Python HTTP API Servers with Flask and Flask RESTful
- JSON data format
- Python projects, dependencies and virtual environments (uv)

## Application Creation

Install uv (if needed) following the [official instructions](https://docs.astral.sh/uv/getting-started/installation/), e.g.:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Create a new project `http-api` that will contain the application files and the Docker configuration files.
The `--package` option creates a project with the `src` layout (the code in `src/http_api`) that can be installed and
run through a command:

```bash
uv init --package --python 3.12 http-api
cd http-api
```

Add the dependencies of the application: uv adds them to `pyproject.toml`, resolves their versions in `uv.lock`
and installs them in the virtual environment of the project (`.venv`):

```bash
uv add "flask>=2.3,<3" "flask-restful>=0.3.10" "pyyaml>=6.0"
```

`uv init` creates `pyproject.toml`, `.python-version`, `uv.lock` (after `uv add`), a `README.md` and the package
`src/http_api` with an example `main()` function in `__init__.py`. Edit the generated files as follows:

- in `pyproject.toml`, set the `description` and replace the example `http-api` command of the `[project.scripts]`
  section with the `http-api-server` command, that runs the `main()` function of the `api_server` module;
- remove the `readme` field (and the generated `README.md`): the Docker image only contains the files needed to run the
  application, and uv requires the README declared in `pyproject.toml` to install the project;
- replace the example `main()` function of `src/http_api/__init__.py` with a docstring describing the package.

The resulting `pyproject.toml` is the following:

```toml
[project]
name = "http-api"
version = "0.1.0"
description = "Simple HTTP RESTful API (Flask + Flask-RESTful) exposing a test endpoint, packaged as a Docker container"
requires-python = ">=3.10"
dependencies = [
    "flask>=2.3,<3",
    "flask-restful>=0.3.10",
    "pyyaml>=6.0",
]

[project.scripts]
http-api-server = "http_api.api_server:main"

[build-system]
requires = ["uv_build>=0.13.0,<0.14"]
build-backend = "uv_build"

[tool.uv.build-backend]
module-name = "http_api"
```

Inside the `src/http_api` package create the `resources` package (with an `__init__.py` file) and the
`test_resource.py` file that contains the following code:

```python
from typing import Any

from flask_restful import Resource


class TestResource(Resource):
    """ Test resource returning a fixed JSON object """

    def __init__(self, **kwargs: Any) -> None:
        # Initialize a default response
        self.default_response = {"location_id": "test", "location_name": "test", "latitude": 0.0, "longitude": 0.0}

    def get(self) -> Any:
        # Return the default response and 200 OK code
        return self.default_response, 200
```

This file contains the implementation of the API resource that will be exposed by the API server.
In this case, the API server exposes a single endpoint `/api/iot/test` that returns a JSON response with a test message.

Create a new file `conf.yaml` in the project root that contains the following configuration:

```yaml
# API Server configuration
rest:
  api_prefix: "/api/iot"
  host: "0.0.0.0"
  port: 7070
```

This file contains the configuration of the API server with the binding host and port, and the API base path.
It will be used by the API server to read its configuration and then run the server.

The configuration file is read by the `ConfigLoader` class. Create the `config` package (with an `__init__.py` file) and
the `config_loader.py` file with the following code. The file is searched in the current working directory and then in
the project root, and its values are merged over the default configuration:

```python
from pathlib import Path
from typing import Any

import yaml


class ConfigLoader:
    """
    ConfigLoader class loads the YAML configuration file of the service (e.g., conf.yaml).

    A relative path is searched in the current working directory and, if not found, in the service root directory,
    so the service can be started from any folder.
    """

    # Service root directory: src/http_api/config/config_loader.py -> 3 levels up
    PROJECT_ROOT_DIR = Path(__file__).resolve().parents[3]

    @classmethod
    def resolve_path(cls, config_file: str | Path) -> Path:
        """
        Resolve the path of a configuration file
        :param config_file: Absolute path or path relative to the working directory or to the project root
        :return: The path of the existing configuration file
        """

        config_path = Path(config_file)
        if config_path.is_absolute():
            candidate_paths = [config_path]
        else:
            candidate_paths = [Path.cwd() / config_path, cls.PROJECT_ROOT_DIR / config_path]

        for candidate_path in candidate_paths:
            if candidate_path.is_file():
                return candidate_path

        raise FileNotFoundError(f"Configuration file not found. Searched in: {[str(p) for p in candidate_paths]}")

    @classmethod
    def load(cls, config_file: str | Path, default_configuration: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Load a YAML configuration file, merging its values over the default configuration
        :param config_file: Path of the YAML file (see resolve_path)
        :param default_configuration: Default values used for the parameters not defined in the file
        :return: The configuration dictionary
        """

        configuration: dict[str, Any] = dict(default_configuration or {})

        config_path = cls.resolve_path(config_file)
        with open(config_path, "r", encoding="utf-8") as file:
            file_configuration = yaml.safe_load(file) or {}

        # Merge the file values over the defaults (one level of nested sections, e.g., "rest" or "web")
        for key, value in file_configuration.items():
            if isinstance(value, dict) and isinstance(configuration.get(key), dict):
                configuration[key] = {**configuration[key], **value}
            else:
                configuration[key] = value

        print(f"Read Configuration from file ({config_path}): {configuration}")
        return configuration
```

Now we can create the `api_server.py` file in the `src/http_api` package that contains the following code:

```python
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
```

This file contains the implementation of the API server that exposes the `TestResource` resource that we have
previously implemented. The API server reads the configuration from the `conf.yaml` file and then starts the HTTP
server on the specified host and port. The server also handles the `SIGTERM` signal, that is sent by Docker when the
container is stopped (see [Stop & Remove the Container](#stop--remove-the-container)).

Before creating the container, test the application locally:

```bash
uv run http-api-server
```

and open [http://localhost:7070/api/iot/test](http://localhost:7070/api/iot/test). Stop the server with `CTRL+C`.

Now that we have created the application files, we can proceed to create the Docker configuration files.

## Dockerfile

In the `http-api` folder create a new file named `Dockerfile` that contains the following code:

```dockerfile
# Base image with Python 3.12 (Debian slim)
FROM python:3.12-slim

# Copy the uv binary from the official uv image (pinned version for reproducible builds)
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /uvx /bin/

# Set the target container working directory to /app
WORKDIR /app

# uv settings: compile the bytecode at install time, use the Python of the image (no downloads)
# and print the application output without buffering
ENV UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

# 1. Install only the dependencies, using the locked versions of uv.lock.
#    This layer is rebuilt only when pyproject.toml or uv.lock change, not when the source code changes
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

# 2. Copy the source code and the default configuration, then install the project itself
COPY src ./src
COPY conf.yaml ./conf.yaml
RUN uv sync --frozen --no-dev

# Use the virtual environment created by uv
ENV PATH="/app/.venv/bin:$PATH"

# Exposed Port of the API Server
EXPOSE 7070

# Run the target application (command declared in pyproject.toml)
CMD ["http-api-server"]
```

In this example with respect to the previously presented Dockerfile we used:

- The `python:3.12-slim` image as the base image instead of the `ubuntu` image, so we do not need to install Python 3.
- The `COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /uvx /bin/` instruction, that copies the uv executable from its
  official image (a **multi-stage copy**): no installation script is needed and the version of uv is pinned.
- Two `uv sync` steps to exploit the **layer cache** of Docker:
  - the first one copies only `pyproject.toml`, `uv.lock` and `.python-version` and installs the dependencies
    (`--no-install-project`). This layer is rebuilt only when the dependencies change;
  - the second one copies the source code and installs the project itself. Changing the code only rebuilds these last
    layers, so the dependencies are not downloaded again at each build.
- The `--frozen` option, that installs exactly the versions of `uv.lock` (the build fails if the lock file is not up
  to date), and the `--no-dev` option, that skips the development dependencies.
- The `UV_COMPILE_BYTECODE` variable, that compiles the Python files at build time to speed up the startup of the
  container, and `UV_PYTHON_DOWNLOADS=never`, that forces uv to use the Python of the base image.
- The `PATH` variable, extended with the virtual environment created by uv (`/app/.venv/bin`), so that the `CMD` can
  run the `http-api-server` command declared in `pyproject.toml`.
- The `EXPOSE` instruction exposes port 7070, which is the port on which the API server will run. This is just a declaration and does not actually publish the port that is done when running the container.
- The `PYTHONUNBUFFERED` variable ensures that all output from the application is immediately flushed to
the logs (**without this variable we are not able to read the logs of the Python application**), which is useful for real-time monitoring and debugging.

Create also the `.dockerignore` file, that excludes from the **build context** (the files sent to Docker to build the
image) the local virtual environment and the caches:

```text
# Files not sent to the Docker build context
.venv/
**/__pycache__/
.mypy_cache/
.idea/
.git/
```

## Build the Container

In order to build the container, we need to run the following command **in the same directory where the Dockerfile is located**.

```bash
docker build -t http-api:0.1 .
```

The output reports the execution of each instruction of the Dockerfile (the details depend on the Docker version):

```bash
 => [internal] load build definition from Dockerfile
 => [internal] load metadata for ghcr.io/astral-sh/uv:0.13.0
 => [internal] load metadata for docker.io/library/python:3.12-slim
 => [internal] load .dockerignore
 => [stage-0 1/8] FROM docker.io/library/python:3.12-slim
 => [internal] load build context
 => [stage-0 2/8] COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /uvx /bin/
 => [stage-0 3/8] WORKDIR /app
 => [stage-0 4/8] COPY pyproject.toml uv.lock .python-version ./
 => [stage-0 5/8] RUN uv sync --frozen --no-dev --no-install-project
 => [stage-0 6/8] COPY src ./src
 => [stage-0 7/8] COPY conf.yaml ./conf.yaml
 => [stage-0 8/8] RUN uv sync --frozen --no-dev
 => exporting to image
 => => naming to docker.io/library/http-api:0.1
```

If we change only the source code and build the image again, the steps from 2 to 5 are reported as `CACHED`
and only the last steps are executed: the dependencies are not installed again.

At the end of the process, the image `http-api:0.1` is created and available on the Docker host.
To check the image you can run the following command:

```bash
docker images
```

## Run the Container

Now that the image is built, we can run the container using the following parameters:

- exposing the port on the `7070` using `-p 7070:7070`
- naming the container `http-api` using `--name=http-api`
- running it in daemon mode `-d` to run in the background without blocking the terminal
- setting a restart always mode with `--restart always`
- the final parameter is the name of the image `http-api:0.1` with the tag `0.1`

```bash
docker run --name=http-api -p 7070:7070 --restart always -d http-api:0.1
```

The output will be something like:

```bash
c3561fbbd630330d33c34cb21ebb87bd3e265e2931257b7f100bd9cd7e4b80b6
```

This command starts the container in the background and returns the container ID.
We can use the container ID to check the status of the container and view the logs.

Through the following command we can check the status of the container:

```bash
docker ps
```

The output will be something like:

```bash
CONTAINER ID   IMAGE          COMMAND             CREATED          STATUS          PORTS                    NAMES
c3561fbbd630   http-api:0.1   "http-api-server"   32 seconds ago   Up 30 seconds   0.0.0.0:7070->7070/tcp   http-api
```

Now using the container ID (or its name) we can check the logs of the container:

```bash
docker logs --tail 100 -f c3561fbbd630
```

The output will be something like:

```bash
Read Configuration from file (/app/conf.yaml): {'rest': {'api_prefix': '/api/iot', 'host': '0.0.0.0', 'port': 7070}}
Starting HTTP RESTful API Server ...
HTTP RESTful API Server running on http://0.0.0.0:7070/api/iot/test
```

As you can see the application is running and the API server is listening on the port 7070 of all the network
interfaces of the container (`0.0.0.0`). The API server is accessible from the host machine using the host IP address
(or `localhost`) and the port 7070. This is due to the fact that the container is running in a bridge network and the
port is published to the host machine with the `-p 7070:7070` parameter.

Now you can access the API using the following URL: [http://localhost:7070/api/iot/test](http://localhost:7070/api/iot/test)
and you should receive the following response:

```json
{
  "location_id": "test",
  "location_name": "test",
  "latitude": 0.0,
  "longitude": 0.0
}
```

## Run the Container with Configuration File

The file `test_conf.yaml` (in the `http-api` folder) contains a changed configuration with a different `port`:

```yaml
# API Server configuration with a different port (passed to the container at runtime)
rest:
  api_prefix: "/api/iot"
  host: "0.0.0.0"
  port: 5050
```

You can pass the local file to overwrite the original one in the
image container using the syntax `-v local_file_path:container_image_file_path` as follows:

```bash
docker run --name=http-api -p 5050:5050 -v <PATH_TO_FILE>/test_conf.yaml:/app/conf.yaml --restart always -d http-api:0.1
```

On Linux and macOS (and in Windows PowerShell) you can use `${PWD}` to automatically retrieve the path to the current local folder

```bash
docker run --name=http-api -p 5050:5050 -v ${PWD}/test_conf.yaml:/app/conf.yaml --restart always -d http-api:0.1
```

Now you can access the API on port 5050 instead of 7070 using the following URL: [http://localhost:5050/api/iot/test](http://localhost:5050/api/iot/test)

### Stop & Remove the Container

In order to stop and remove the container you can use the following commands:

```bash
docker stop http-api
docker rm http-api
```

The first command stops the container and the second command removes the container from the Docker host.
`docker stop` sends the `SIGTERM` signal to the main process of the container: since the API server handles it, the
container stops immediately (otherwise Docker would wait for 10 seconds and then kill the process).
The remove will also remove the container logs and the container configuration.
If a container is stopped and not removed it can be restarted using the `docker start` command passing the container ID or the container name.
Restarting a container will not remove the logs and the configuration and the container will start from the last state.
