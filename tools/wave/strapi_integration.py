from __future__ import absolute_import
from __future__ import unicode_literals
import json
import logging

try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
except ImportError:
    from urllib2 import Request, urlopen, HTTPError, URLError

from .utils.serializer import millis_to_iso


class StrapiSessionUpsertClient(object):
    def __init__(self, configuration):
        if configuration is None:
            configuration = {}
        self._enabled = bool(configuration.get("enabled", False))
        self._base_url = configuration.get("base_url", "")
        self._upsert_path = configuration.get("upsert_path", "/api/test-sessions/upsert")
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

    def _session_payload(self, session):
        return {
            "token": session.token,
            "user_agent": session.user_agent,
            "status": session.status,
            "date_started": millis_to_iso(session.date_started),
        }
