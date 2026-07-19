from __future__ import absolute_import
from __future__ import unicode_literals
import json
import logging

try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
    from urllib.parse import urlencode
except ImportError:
    from urllib2 import Request, urlopen, HTTPError, URLError
    from urllib import urlencode

from .utils.serializer import millis_to_iso


class StrapiSessionUpsertClient(object):
    def __init__(self, configuration):
        if configuration is None:
            configuration = {}
        self._enabled = bool(configuration.get("enabled", False))
        self._base_url = configuration.get("base_url", "")
        self._upsert_path = configuration.get("upsert_path", "/api/test-sessions/upsert")
        self._overview_path = configuration.get("overview_path", "/api/test-sessions-overview")
        self._delete_by_token_path_template = configuration.get(
            "delete_by_token_path_template",
            "/api/test-sessions/by-token/{token}"
        )
        self._device_overview_path = configuration.get("device_overview_path", "/api/devices-overview")
        self._device_update_path_template = configuration.get(
            "device_update_path_template",
            "/api/devices/by-device-id/{device_id}"
        )
        self._device_upsert_path = configuration.get("device_upsert_path", "/api/devices/upsert")
        self._api_token = configuration.get("api_token", "")
        self._timeout_ms = configuration.get("timeout_ms", 2000)
        self._logger = logging.getLogger("wave-server.strapi")

    def upsert_session(self, session):
        if not self._enabled:
            return False
        if session is None:
            return False
        if not self._base_url:
            self._logger.warning("Strapi upsert skipped: base_url is empty")
            return False

        payload = self._session_payload(session)
        request_url = "{}/{}".format(
            self._base_url.rstrip("/"),
            self._upsert_path.lstrip("/")
        )

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._api_token:
            headers["Authorization"] = "Bearer {}".format(self._api_token)

        timeout = float(self._timeout_ms) / 1000.0
        body = json.dumps(payload).encode("utf-8")
        request = Request(request_url, data=body, headers=headers)
        request.get_method = lambda: "POST"

        try:
            response = urlopen(request, timeout=timeout)
            status_code = response.getcode()
            return status_code >= 200 and status_code < 300
        except HTTPError as error:
            self._logger.warning(
                "Strapi upsert failed with status %s for token %s",
                error.code,
                session.token
            )
            return False
        except URLError as error:
            self._logger.warning(
                "Strapi upsert failed for token %s: %s",
                session.token,
                str(error)
            )
            return False
        except Exception as error:
            self._logger.warning(
                "Unexpected Strapi upsert failure for token %s: %s",
                session.token,
                str(error)
            )
            return False

    def upsert_device_metadata(self, session):
        if not self._enabled:
            return False
        if session is None:
            return False
        if not self._base_url:
            self._logger.warning("Strapi device upsert skipped: base_url is empty")
            return False

        payload = self._device_payload(session)
        request_url = "{}/{}".format(
            self._base_url.rstrip("/"),
            self._device_upsert_path.lstrip("/")
        )

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._api_token:
            headers["Authorization"] = "Bearer {}".format(self._api_token)

        timeout = float(self._timeout_ms) / 1000.0
        body = json.dumps(payload).encode("utf-8")
        request = Request(request_url, data=body, headers=headers)
        request.get_method = lambda: "POST"

        try:
            response = urlopen(request, timeout=timeout)
            status_code = response.getcode()
            return status_code >= 200 and status_code < 300
        except HTTPError as error:
            self._logger.warning(
                "Strapi device upsert failed with status %s for token %s",
                error.code,
                session.token
            )
            return False
        except URLError as error:
            self._logger.warning(
                "Strapi device upsert failed for token %s: %s",
                session.token,
                str(error)
            )
            return False
        except Exception as error:
            self._logger.warning(
                "Unexpected Strapi device upsert failure for token %s: %s",
                session.token,
                str(error)
            )
            return False

    def _session_payload(self, session):
        return {
            "token": session.token,
            "user_agent": session.user_agent,
            "session_status": session.status,
            "date_started": millis_to_iso(session.date_started),
            "test_files": self._calculate_test_files(session),
        }

    def _calculate_test_files(self, session):
        if session is None:
            return 0
        test_state = getattr(session, "test_state", None)
        if not isinstance(test_state, dict):
            return 0

        test_files = 0
        for api in test_state:
            api_state = test_state.get(api) or {}
            total = api_state.get("total", 0)
            try:
                test_files += int(total)
            except (TypeError, ValueError):
                continue
        return test_files

    def list_test_sessions(self):
        if not self._enabled:
            return []
        if not self._base_url:
            self._logger.warning("Strapi list skipped: base_url is empty")
            return []

        request_url = "{}/{}".format(
            self._base_url.rstrip("/"),
            self._overview_path.lstrip("/")
        )

        headers = {
            "Accept": "application/json",
        }
        if self._api_token:
            headers["Authorization"] = "Bearer {}".format(self._api_token)

        timeout = float(self._timeout_ms) / 1000.0
        request = Request(request_url, headers=headers)
        request.get_method = lambda: "GET"

        try:
            response = urlopen(request, timeout=timeout)
            raw_data = response.read()
            if not raw_data:
                return []
            json_data = json.loads(raw_data.decode("utf-8"))
            if isinstance(json_data, list):
                data = json_data
            else:
                data = json_data.get("data", [])
            sessions_by_token = {}
            for item in data:
                attributes = item.get("attributes", item)
                token = attributes.get("token")
                if not token:
                    continue
                session = {
                    "token": token,
                    "user_agent": attributes.get("user_agent") or "",
                    "session_status": attributes.get("session_status") or "",
                    "date_started": attributes.get("date_started"),
                    "test_files": attributes.get("test_files", 0),
                }
                existing_session = sessions_by_token.get(token)
                if existing_session is None or self._is_preferred_test_session(session, existing_session):
                    sessions_by_token[token] = session

            sessions = list(sessions_by_token.values())
            device_id_by_session_token, device_id_by_user_agent = self._build_device_lookup_maps()
            for session in sessions:
                token = session.get("token")
                user_agent = session.get("user_agent") or ""
                device_id = device_id_by_session_token.get(token)
                if device_id is None and user_agent:
                    device_id = device_id_by_user_agent.get(user_agent)
                session["device_id"] = device_id if device_id is not None else ""
            sessions.sort(
                key=lambda session: session.get("date_started") or "",
                reverse=True
            )
            return sessions
        except HTTPError as error:
            self._logger.warning("Strapi list failed with status %s", error.code)
            return []
        except URLError as error:
            self._logger.warning("Strapi list failed: %s", str(error))
            return []
        except Exception as error:
            self._logger.warning("Unexpected Strapi list failure: %s", str(error))
            return []

    def _is_preferred_test_session(self, candidate, existing):
        candidate_date_started = candidate.get("date_started")
        existing_date_started = existing.get("date_started")
        if candidate_date_started and not existing_date_started:
            return True
        if existing_date_started and not candidate_date_started:
            return False

        candidate_status = candidate.get("session_status") or ""
        existing_status = existing.get("session_status") or ""
        if candidate_status != "pending" and existing_status == "pending":
            return True
        if existing_status != "pending" and candidate_status == "pending":
            return False

        if candidate_date_started and existing_date_started:
            return candidate_date_started > existing_date_started

        return False

    def delete_test_session_by_token(self, token):
        if not self._enabled:
            return False
        if not self._base_url:
            self._logger.warning("Strapi delete skipped: base_url is empty")
            return False
        if not token:
            return False

        headers = {
            "Accept": "application/json",
        }
        if self._api_token:
            headers["Authorization"] = "Bearer {}".format(self._api_token)

        timeout = float(self._timeout_ms) / 1000.0
        delete_path = self._delete_by_token_path_template.format(token=token)
        delete_url = "{}/{}".format(
            self._base_url.rstrip("/"),
            delete_path.lstrip("/")
        )
        delete_request = Request(delete_url, headers=headers)
        delete_request.get_method = lambda: "DELETE"

        try:
            delete_response = urlopen(delete_request, timeout=timeout)
            status_code = delete_response.getcode()
            return status_code >= 200 and status_code < 300
        except HTTPError as error:
            self._logger.warning(
                "Strapi delete failed with status %s for token %s",
                error.code,
                token
            )
            return False
        except URLError as error:
            self._logger.warning(
                "Strapi delete failed for token %s: %s",
                token,
                str(error)
            )
            return False
        except Exception as error:
            self._logger.warning(
                "Unexpected Strapi delete failure for token %s: %s",
                token,
                str(error)
            )
            return False

    def list_devices(self):
        if not self._enabled:
            return []
        if not self._base_url:
            self._logger.warning("Strapi devices list skipped: base_url is empty")
            return []

        request_url = "{}/{}".format(
            self._base_url.rstrip("/"),
            self._device_overview_path.lstrip("/")
        )

        headers = {
            "Accept": "application/json",
        }
        if self._api_token:
            headers["Authorization"] = "Bearer {}".format(self._api_token)

        timeout = float(self._timeout_ms) / 1000.0
        request = Request(request_url, headers=headers)
        request.get_method = lambda: "GET"

        try:
            response = urlopen(request, timeout=timeout)
            raw_data = response.read()
            if not raw_data:
                return []
            json_data = json.loads(raw_data.decode("utf-8"))
            if isinstance(json_data, list):
                data = json_data
            else:
                data = json_data.get("data", [])

            devices_by_key = {}
            for item in data:
                attributes = item.get("attributes", item)
                device_id = attributes.get("device_id")
                user_agent = attributes.get("user_agent") or ""
                hbbtv_version = attributes.get("hbbtv_version") or ""
                manufacturer = attributes.get("manufacturer") or ""
                model = attributes.get("model") or ""
                year = attributes.get("year")
                if device_id is None:
                    key = (user_agent, hbbtv_version)
                else:
                    key = (device_id,)

                candidate = {
                    "device_id": device_id,
                    "manufacturer": manufacturer,
                    "model": model,
                    "year": year,
                    "user_agent": user_agent,
                    "hbbtv_version": hbbtv_version,
                    "_updated_at": attributes.get("updatedAt") or attributes.get("updated_at") or "",
                }

                existing = devices_by_key.get(key)
                if existing is None or self._is_preferred_device(candidate, existing):
                    devices_by_key[key] = candidate

            devices = []
            for device in devices_by_key.values():
                cleaned = dict(device)
                cleaned.pop("_updated_at", None)
                devices.append(cleaned)
            return devices
        except HTTPError as error:
            self._logger.warning("Strapi devices list failed with status %s", error.code)
            return []
        except URLError as error:
            self._logger.warning("Strapi devices list failed: %s", str(error))
            return []
        except Exception as error:
            self._logger.warning("Unexpected Strapi devices list failure: %s", str(error))
            return []

    def _is_preferred_device(self, candidate, existing):
        def _score(device):
            populated_fields = 0
            if (device.get("manufacturer") or "").strip() != "":
                populated_fields += 1
            if (device.get("model") or "").strip() != "":
                populated_fields += 1
            if device.get("year") is not None:
                populated_fields += 1
            return populated_fields

        candidate_score = _score(candidate)
        existing_score = _score(existing)
        if candidate_score != existing_score:
            return candidate_score > existing_score

        candidate_updated = candidate.get("_updated_at") or ""
        existing_updated = existing.get("_updated_at") or ""
        if candidate_updated != existing_updated:
            return candidate_updated > existing_updated

        return False

    def update_device(self, device_id, manufacturer=None, model=None, year=None):
        if not self._enabled:
            return False
        if not self._base_url:
            self._logger.warning("Strapi device update skipped: base_url is empty")
            return False
        if device_id is None:
            return False

        update_path = self._device_update_path_template.format(device_id=device_id)
        request_url = "{}/{}".format(
            self._base_url.rstrip("/"),
            update_path.lstrip("/")
        )

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._api_token:
            headers["Authorization"] = "Bearer {}".format(self._api_token)

        payload = {
            "manufacturer": manufacturer,
            "model": model,
            "year": year,
        }

        timeout = float(self._timeout_ms) / 1000.0
        body = json.dumps(payload).encode("utf-8")
        request = Request(request_url, data=body, headers=headers)
        request.get_method = lambda: "PUT"

        try:
            response = urlopen(request, timeout=timeout)
            status_code = response.getcode()
            return status_code >= 200 and status_code < 300
        except HTTPError as error:
            self._logger.warning(
                "Strapi device update failed with status %s for device_id %s",
                error.code,
                str(device_id)
            )
            return False
        except URLError as error:
            self._logger.warning(
                "Strapi device update failed for device_id %s: %s",
                str(device_id),
                str(error)
            )
            return False
        except Exception as error:
            self._logger.warning(
                "Unexpected Strapi device update failure for device_id %s: %s",
                str(device_id),
                str(error)
            )
            return False

    def _build_device_lookup_maps(self):
        device_id_by_session_token = {}
        device_id_by_user_agent = {}

        if not self._enabled:
            return device_id_by_session_token, device_id_by_user_agent
        if not self._base_url:
            return device_id_by_session_token, device_id_by_user_agent

        request_url = "{}/{}".format(
            self._base_url.rstrip("/"),
            self._device_overview_path.lstrip("/")
        )

        headers = {
            "Accept": "application/json",
        }
        if self._api_token:
            headers["Authorization"] = "Bearer {}".format(self._api_token)

        timeout = float(self._timeout_ms) / 1000.0
        request = Request(request_url, headers=headers)
        request.get_method = lambda: "GET"

        try:
            response = urlopen(request, timeout=timeout)
            raw_data = response.read()
            if not raw_data:
                return device_id_by_session_token, device_id_by_user_agent

            json_data = json.loads(raw_data.decode("utf-8"))
            if isinstance(json_data, list):
                data = json_data
            else:
                data = json_data.get("data", [])

            for item in data:
                attributes = item.get("attributes", item)
                device_id = attributes.get("device_id")
                user_agent = attributes.get("user_agent") or ""
                if user_agent and device_id is not None and user_agent not in device_id_by_user_agent:
                    device_id_by_user_agent[user_agent] = device_id

                token_values = self._extract_token_list(attributes.get("token"))
                for token in token_values:
                    if token and device_id is not None and token not in device_id_by_session_token:
                        device_id_by_session_token[token] = device_id
        except Exception:
            return device_id_by_session_token, device_id_by_user_agent

        return device_id_by_session_token, device_id_by_user_agent

    def _extract_token_list(self, value):
        if isinstance(value, list):
            return [token for token in value if isinstance(token, str) and token]
        if isinstance(value, str):
            raw = value.strip()
            if raw == "":
                return []
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [token for token in parsed if isinstance(token, str) and token]
            except Exception:
                return [raw]
        return []

    def _device_payload(self, session):
        user_agent = session.user_agent or ""
        hbbtv_version = "---"
        needle = "HbbTV"
        index = user_agent.find(needle)
        if index != -1:
            start = index + len(needle)
            hbbtv_version = user_agent[start:start + 6]

        return {
            "token": session.token,
            "user_agent": user_agent,
            "hbbtv_version": hbbtv_version,
        }
