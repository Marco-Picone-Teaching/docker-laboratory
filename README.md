# Docker Laboratory

This Laboratory has the objective to provide a simple step-by-step guide to learn 
how to build a simple IoT application using Docker containers exposing a HTTP RESTful API with a single endpoint that returns a JSON response.

The implementation is based on the following Python Frameworks 

- Flask: https://flask.palletsprojects.com/en/2.0.x/
- Flask RESTful: https://flask-restful.readthedocs.io/en/latest/index.html

APIs are exposed through a configurable port (7070) and accessible locally at: [http://127.0.0.1:7070/api/iot/test](http://127.0.0.1:7070/api/iot/test)

Main characteristics of the application are:

- **API Endpoint**: `/api/iot/test`
- **HTTP Method**: `GET`
- **Response**: JSON object with a message test message
- **Configuration File**: `conf.yaml` with the API configuration with binding host and port, and the API base path

To simplify the building and the structure of the container the application has been organized with the following structure:

- **app**: Contains the Python application files allowing to easily copy them to the container and have a clear separation between the application and the Docker configuration.
- **requirements.txt**: Contains the Python dependencies required by the application.
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
- Python Requirements and Virtual Environments

## Application Creation 

Create a new folder `http-api` that will contain the application files and the Docker configuration files.
Follow the steps below to create the application files and the Docker configuration files.

Create inside the `http-api` folder the `requirements.txt` file contains the following dependencies:

```txt
flask_restful~=0.3.10
Flask~=2.3.2
requests~=2.31.0
pyyaml~=6.0.1
```

Create the `app` folder that will contain the Python application files.
Inside the `app` folder create the `resources` folder that will contain the API resources files.
Inside the `resources` folder create an empty `__init__.py` file and the `test_resource.py` file that contains the following code:

```python
from flask_restful import Resource


class TestResource(Resource):

    def __init__(self, **kwargs):
        # Initialize a default response
        self.default_response = {"location_id": "test", "location_name": "test", "latitude": 0.0, "longitude": 0.0}

    def get(self):
        # Return the default response and 200 OK code
        return self.default_response, 200  # return data and 200 OK code
```

This file contains the implementation of the API resource that will be exposed by the API server.
In this case, the API server exposes a single endpoint `/api/iot/test` that returns a JSON response with a test message.

Create a new file `conf.yaml` in the `app` folder that contains the following configuration:

```yaml
rest:
  api_prefix: "/api/iot"
  host: "0.0.0.0"
  port: 7070
```

This file contains the configuration of the API server with the binding host and port, and the API base path.
It will be used in the api server to read the default configuration and then run the API server.

Now we can create the `api_server.py` file in the `app` folder that contains the following code:

```python
from flask import Flask
from flask_restful import Api
from resources.test_resource import TestResource
import yaml

# Default Values
CONF_FILE_PATH = "conf.yaml"

# Read Configuration from target Configuration File Path
def read_configuration_file():
    global configuration_dict

    with open(CONF_FILE_PATH, 'r') as file:
        configuration_dict = yaml.safe_load(file)

    return configuration_dict

# Read Configuration file
configuration_dict = read_configuration_file()

print("Read Configuration from file ({}): {}".format(CONF_FILE_PATH, configuration_dict))

app = Flask(__name__)
api = Api(app)

print("Starting HTTP RESTful API Server ...")

api.add_resource(TestResource, configuration_dict['rest']['api_prefix'] + '/test',
                 endpoint="TestEndPoint",
                 methods=['GET'])

if __name__ == '__main__':

    app.run(host=configuration_dict['rest']['host'], port=configuration_dict['rest']['port'])  # run our Flask app
```

This file contains the implementation of the API server that will expose the API resources and in particular the `TestResource` resource
tha we have previously implemented. The API server reads the configuration from the `conf.yaml` file and then starts the API server on the specified host and port.

Now that we have created the application files, we can proceed to create the Docker configuration files.

## Dockerfile

In the `http-api` folder create a new file named `Dockerfile` that contains the following code:

```dockerfile
FROM python:3.9-slim-buster

# Copy Application Files & Requirements to /app
COPY ./app /app
COPY requirements.txt /app/requirements.txt

# Set the target container working directory to /app
WORKDIR /app

# Install Python Application Requirements
RUN pip3 install -r requirements.txt

# Exposed Port of the API Server
EXPOSE 7070

# Python Container Application Configurations
ENV PYTHONPATH "/app/"
ENV PYTHONUNBUFFERED 1

# Run the target application
CMD [ "python3", "api_server.py" ]
```

In this example with respect to the previously presented Dockerfile we used:

- The `python:3.9-slim-buster` image as the base image instead of the `ubuntu` image and we do not need to install Python 3.
- The `EXPOSE` instruction exposes port 7070, which is the port on which the API server will run. This is just a declaration and does not actually publish the port that is done when running the container.
- The `PYTHONPATH` variable ensures that Python can find and import modules from the /app directory. 
- The `PYTHONUNBUFFERED` variable ensures that all output from the application is immediately flushed to 
the logs (**without this variable we are not able to read the logs of the Python application**), which is useful for real-time monitoring and debugging.

## Build the Container

In order to build the container, we need to run the following command **in the same directory where the Dockerfile is located**.

```bash
docker build -t http-api:0.1 .
```

The output will be something like:

```bash
[+] Building 8.6s (10/10) FINISHED                                                                                                                                                                   
 => [internal] load build definition from Dockerfile                                                                                                                                            0.0s
 => => transferring dockerfile: 532B                                                                                                                                                            0.0s
 => [internal] load .dockerignore                                                                                                                                                               0.0s
 => => transferring context: 2B                                                                                                                                                                 0.0s
 => [internal] load metadata for docker.io/library/python:3.9-slim-buster                                                                                                                       1.7s
 => CACHED [1/5] FROM docker.io/library/python:3.9-slim-buster@sha256:320a7a4250aba4249f458872adecf92eea88dc6abd2d76dc5c0f01cac9b53990                                                          0.0s
 => [internal] load build context                                                                                                                                                               0.0s
 => => transferring context: 2.64kB                                                                                                                                                             0.0s
 => [2/5] COPY ./app /app                                                                                                                                                                       0.0s
 => [3/5] COPY requirements.txt /app/requirements.txt                                                                                                                                           0.0s
 => [4/5] WORKDIR /app                                                                                                                                                                          0.0s
 => [5/5] RUN pip3 install -r requirements.txt                                                                                                                                                  6.3s
 => exporting to image                                                                                                                                                                          0.3s
 => => exporting layers                                                                                                                                                                         0.3s
 => => writing image sha256:191b6fa4328237bdf1eabbacc89440a558ca9aaf2f64cc6bd1269426bd867c06                                                                                                    0.0s 
 => => naming to docker.io/library/http-api:0.1                                                                                                                                                    0.0s
```

At the end of the process, the image `http-api:0.1` is created and available on the Docker host.
The check the image you can run the following command:

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
➜  http-api git:(main) ✗ docker run --name=http-api -p 7070:7070 --restart always -d http-api:0.1
7df2a5714affbb051bedf25a64c43bdd47dce010ea0173387565ab1df2935535
```

This command starts the container in the background and returns the container ID.
We can use the container ID to check the status of the container and view the logs.

Through the following command we can check the status of the container:

```bash
docker ps
```

The output will be something like:

```bash
CONTAINER ID   IMAGE                                COMMAND                  CREATED          STATUS                   PORTS                      NAMES
7df2a5714aff   http-api:0.1                            "python3 api_server.…"   32 seconds ago   Up 30 seconds            0.0.0.0:7070->7070/tcp     http-api
```

Now using the container ID we can check the logs of the container:

```bash
docker logs --tail 100 -f 7df2a5714aff
```

The output will be something like:

```bash
Read Configuration from file (conf.yaml): {'rest': {'api_prefix': '/api/iot', 'host': '0.0.0.0', 'port': 7070}}
Starting HTTP RESTful API Server ...
 * Serving Flask app 'api_server'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:7070
 * Running on http://172.17.0.3:7070
Press CTRL+C to quit
```

As you can see the application is running and the API server is listening on the port 7070.
The reported IP addresses are the localhost and the container IP address but the API server is accessible from host machine using the host IP address and the port 7070.
This is due to the fact that the container is running in a bridge network and the port is exposed to the host machine
with the `-p 7070:7070` parameter.

Now you can access the API using the following URL: [http://localhost:7070/api/iot/test](http://localhost:7070/api/iot/test)
and you should receive the following response:

```json
{
  "location_id": "test",
  "location_name": "test",
  "latitude": 0,
  "longitude": 0
}
```
## Run the Container with Configuration File

Create a new file `test_conf.yaml` (there is one in the main folder) 
containing a changed configuration with a new `api_prefix` and a different `port` as follows:

```yaml
rest:
  api_prefix: "/api/iot"
  host: "0.0.0.0"
  port: 5050
```

You can pass the local file to overwrite the original on in the 
image container using the syntax `-v local_file_path:container_image_file_path` as follows:

```bash
docker run --name=http-api -p 5050:5050 -v <PATH_TO_FILE>/test_conf.yaml:/app/conf.yaml --restart always -d http-api:0.1
```

On **Linux System** you can use the `${PWD}` command to automatically retrieve the path to the current local folder

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
The remove will also remove the container logs and the container configuration.
If a container is stopped and not removed it can be restarted using the `docker start` command passing the container ID or the container name.
Restarting a container will not remove the logs and the configuration and the container will start from the last state.
