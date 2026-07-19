from __future__ import absolute_import
from __future__ import unicode_literals
import json

from .api_handler import ApiHandler

TOKEN_LENGTH = 36


class GeneralApiHandler(ApiHandler):
    def __init__(
        self,
        web_root,
        read_sessions_enabled,
        import_results_enabled,
        reports_enabled,
        version_string,
        dpctf_version_string,
        test_type_selection_enabled,
        strapi_integration=None
    ):
        super(GeneralApiHandler, self).__init__(web_root)
        self.read_sessions_enabled = read_sessions_enabled
        self.import_results_enabled = import_results_enabled
        self.reports_enabled = reports_enabled
        self.version_string = version_string
        self.dpctf_version_string = dpctf_version_string
        self.test_type_selection_enabled = test_type_selection_enabled
        self._strapi_integration = strapi_integration

    def read_status(self):
        try:
            return {
                "format": "application/json",
                "data": {
                    "version_string": self.version_string,
                    "dpctf_version_string": self.dpctf_version_string,
                    "read_sessions_enabled": self.read_sessions_enabled,
                    "import_results_enabled": self.import_results_enabled,
                    "reports_enabled": self.reports_enabled,
                    "test_type_selection_enabled": self.test_type_selection_enabled
                }
            }
        except Exception:
            self.handle_exception("Failed to read server configuration")
            return {"status": 500}

    def read_test_sessions(self):
        try:
            if self._strapi_integration is None:
                return {
                    "format": "application/json",
                    "data": []
                }
            sessions = self._strapi_integration.list_test_sessions()
            return {
                "format": "application/json",
                "data": sessions
            }
        except Exception:
            self.handle_exception("Failed to read test sessions")
            return {"status": 500}

    def delete_test_session(self, token):
        try:
            if self._strapi_integration is None:
                return {"status": 404}
            deleted = self._strapi_integration.delete_test_session_by_token(token)
            if not deleted:
                return {"status": 404}
            return {
                "format": "application/json",
                "data": {"deleted": True}
            }
        except Exception:
            self.handle_exception("Failed to delete test session")
            return {"status": 500}

    def update_test_session_details(self, token, body):
        try:
            if self._strapi_integration is None:
                return {"status": 404}

            payload = {}
            decoded = body.decode("utf-8") if body is not None else ""
            if decoded != "":
                payload = json.loads(decoded)

            details = payload.get("details", "")
            updated = self._strapi_integration.update_test_session_details_by_token(token, details)
            if not updated:
                return {"status": 404}
            return {
                "format": "application/json",
                "data": {"updated": True}
            }
        except Exception:
            self.handle_exception("Failed to update test session details")
            return {"status": 500}

    def read_devices(self):
        try:
            if self._strapi_integration is None:
                return {
                    "format": "application/json",
                    "data": []
                }
            devices = self._strapi_integration.list_devices()
            return {
                "format": "application/json",
                "data": devices
            }
        except Exception:
            self.handle_exception("Failed to read devices")
            return {"status": 500}

    def update_device(self, device_id, body):
        try:
            if self._strapi_integration is None:
                return {"status": 404}

            payload = {}
            decoded = body.decode("utf-8") if body is not None else ""
            if decoded != "":
                payload = json.loads(decoded)

            manufacturer = payload.get("manufacturer")
            model = payload.get("model")
            year = payload.get("year")

            updated = self._strapi_integration.update_device(
                device_id,
                manufacturer=manufacturer,
                model=model,
                year=year
            )
            if not updated:
                return {"status": 404}
            return {
                "format": "application/json",
                "data": {"updated": True}
            }
        except Exception:
            self.handle_exception("Failed to update device")
            return {"status": 500}

    def handle_request(self, request, response):
        method = request.method
        uri_parts = self.parse_uri(request)

        result = None
        # /api/<function>
        if len(uri_parts) == 2:
            function = uri_parts[1]
            if method == "GET":
                if function == "status":
                    result = self.read_status()
                if function == "test-sessions":
                    result = self.read_test_sessions()
                if function == "devices-overview":
                    result = self.read_devices()

        # /api/test-sessions/<token>
        if len(uri_parts) == 3:
            resource_name = uri_parts[1]
            token = uri_parts[2]
            if method == "DELETE" and resource_name == "test-sessions":
                result = self.delete_test_session(token)
            if method == "PUT" and resource_name == "devices-overview":
                result = self.update_device(token, request.body)

        # /api/test-sessions/<token>/details
        if len(uri_parts) == 4:
            resource_name = uri_parts[1]
            token = uri_parts[2]
            action = uri_parts[3]
            if method == "PUT" and resource_name == "test-sessions" and action == "details":
                result = self.update_test_session_details(token, request.body)

        if result is None:
            response.status = 404
            return

        format = None
        if "format" in result:
            format = result["format"]
            if format == "application/json":
                data = None
                if "data" in result:
                    data = result["data"]
                status = 200
                if "status" in result:
                    status = result["status"]
                self.send_json(data, response, status)
                return

        status = 404
        if "status" in result:
            status = result["status"]
        response.status = status
