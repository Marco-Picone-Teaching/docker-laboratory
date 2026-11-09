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
