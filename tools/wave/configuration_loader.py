from __future__ import absolute_import
from __future__ import unicode_literals
import json
import os
from io import open

from tools.wpt import wpt

DEFAULT_CONFIGURATION_FILE_PATH = os.path.join(wpt.localpaths.repo_root, "./tools/wave/config.default.json")


def parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ["1", "true", "yes", "on"]
    return bool(value)


def parse_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load(configuration_file_path):
    configuration = {}
    if configuration_file_path:
        configuration = load_configuration_file(configuration_file_path)
    default_configuration = load_configuration_file(
        DEFAULT_CONFIGURATION_FILE_PATH)

    configuration["wpt_port"] = configuration.get(
        "ports", default_configuration["ports"]).get(
        "http", default_configuration["ports"]["http"])[0]
    configuration["wpt_ssl_port"] = configuration.get(
        "ports", default_configuration["ports"]).get(
        "https", default_configuration["ports"]["https"])[0]

    web_root = configuration.get(
        "wave", default_configuration["wave"]).get(
        "web_root", default_configuration["wave"]["web_root"])
    if not web_root.startswith("/"):
        web_root = "/" + web_root
    if not web_root.endswith("/"):
        web_root += "/"
    configuration["web_root"] = web_root

    configuration["results_directory_path"] = configuration.get(
        "wave", default_configuration["wave"]).get(
        "results", default_configuration["wave"]["results"])

    configuration["timeouts"] = {}
    configuration["timeouts"]["automatic"] = configuration.get(
        "wave", default_configuration["wave"]).get(
        "timeouts", default_configuration["wave"]["timeouts"]).get(
        "automatic", default_configuration["wave"]["timeouts"]["automatic"])
    configuration["timeouts"]["manual"] = configuration.get(
        "wave", default_configuration["wave"]).get(
        "timeouts", default_configuration["wave"]["timeouts"]).get(
        "manual", default_configuration["wave"]["timeouts"]["manual"])

    configuration["hostname"] = configuration.get(
        "browser_host", default_configuration["browser_host"])

    configuration["import_results_enabled"] = configuration.get(
        "wave", default_configuration["wave"]).get(
        "enable_import_results",
        default_configuration["wave"]["enable_import_results"])

    configuration["read_sessions_enabled"] = configuration.get(
        "wave", default_configuration["wave"]).get(
        "enable_read_sessions",
        default_configuration["wave"]["enable_read_sessions"])

    configuration["persisting_interval"] = configuration.get(
        "wave", default_configuration["wave"]).get(
        "persisting_interval", default_configuration["wave"]["persisting_interval"])

    configuration["event_cache_duration"] = configuration.get(
        "wave", default_configuration["wave"]).get(
        "event_cache_duration", default_configuration["wave"]["event_cache_duration"])

    configuration["tests_directory_path"] = os.getcwd()

    configuration["manifest_file_path"] = os.path.join(
        os.getcwd(), "MANIFEST.json")

    configuration["api_titles"] = configuration.get(
        "wave", default_configuration["wave"]).get(
        "api_titles", default_configuration["wave"]["api_titles"])

    configuration["pre_test_delay"] = configuration.get(
        "wave", default_configuration["wave"]).get(
        "pre_test_delay", default_configuration["wave"]["pre_test_delay"])

    configuration["enable_test_type_selection"] = configuration.get(
        "wave", default_configuration["wave"]).get(
        "enable_test_type_selection", default_configuration["wave"]["enable_test_type_selection"])


    if "wave" in configuration and "host_override" in configuration["wave"]:
        host_override = configuration["wave"]["host_override"]
        if isinstance(host_override, str) and len(host_override) > 0:
            configuration["hostname"] = configuration["wave"]["host_override"]

    configuration["tests_base_url"] = configuration.get(
        "wave", default_configuration["wave"]).get(
        "tests_base_url", default_configuration["wave"]["tests_base_url"])

    default_wave_configuration = default_configuration.get("wave", {})
    configured_wave = configuration.get("wave", {})
    default_strapi = default_wave_configuration.get("strapi", {})
    configured_strapi = configured_wave.get("strapi", {})

    strapi_enabled = parse_bool(
        os.environ.get("STRAPI_ENABLED"),
        configured_strapi.get("enabled", default_strapi.get("enabled", False))
    )
    strapi_base_url = os.environ.get(
        "STRAPI_BASE_URL",
        configured_strapi.get("base_url", default_strapi.get("base_url", ""))
    )
    strapi_upsert_path = os.environ.get(
        "STRAPI_UPSERT_PATH",
        configured_strapi.get("upsert_path", default_strapi.get("upsert_path", "/api/test-sessions/upsert"))
    )
    strapi_overview_path = os.environ.get(
        "STRAPI_OVERVIEW_PATH",
        configured_strapi.get("overview_path", default_strapi.get("overview_path", "/api/test-sessions-overview"))
    )
    strapi_delete_by_token_path_template = os.environ.get(
        "STRAPI_DELETE_BY_TOKEN_PATH_TEMPLATE",
        configured_strapi.get(
            "delete_by_token_path_template",
            default_strapi.get("delete_by_token_path_template", "/api/test-sessions/by-token/{token}")
        )
    )
    strapi_details_update_by_token_path_template = os.environ.get(
        "STRAPI_DETAILS_UPDATE_BY_TOKEN_PATH_TEMPLATE",
        configured_strapi.get(
            "details_update_by_token_path_template",
            default_strapi.get(
                "details_update_by_token_path_template",
                "/api/test-sessions/by-token/{token}/details"
            )
        )
    )
    strapi_device_overview_path = os.environ.get(
        "STRAPI_DEVICE_OVERVIEW_PATH",
        configured_strapi.get("device_overview_path", default_strapi.get("device_overview_path", "/api/devices-overview"))
    )
    strapi_device_update_path_template = os.environ.get(
        "STRAPI_DEVICE_UPDATE_PATH_TEMPLATE",
        configured_strapi.get(
            "device_update_path_template",
            default_strapi.get("device_update_path_template", "/api/devices/by-device-id/{device_id}")
        )
    )
    strapi_device_upsert_path = os.environ.get(
        "STRAPI_DEVICE_UPSERT_PATH",
        configured_strapi.get("device_upsert_path", default_strapi.get("device_upsert_path", "/api/devices/upsert"))
    )
    strapi_api_token = os.environ.get(
        "STRAPI_API_TOKEN",
        configured_strapi.get("api_token", default_strapi.get("api_token", ""))
    )
    strapi_timeout_ms = parse_int(
        os.environ.get("STRAPI_TIMEOUT_MS"),
        configured_strapi.get("timeout_ms", default_strapi.get("timeout_ms", 2000))
    )

    configuration["strapi"] = {
        "enabled": strapi_enabled,
        "base_url": strapi_base_url,
        "upsert_path": strapi_upsert_path,
        "overview_path": strapi_overview_path,
        "delete_by_token_path_template": strapi_delete_by_token_path_template,
        "details_update_by_token_path_template": strapi_details_update_by_token_path_template,
        "device_overview_path": strapi_device_overview_path,
        "device_update_path_template": strapi_device_update_path_template,
        "device_upsert_path": strapi_device_upsert_path,
        "api_token": strapi_api_token,
        "timeout_ms": strapi_timeout_ms,
    }

    return configuration


def load_configuration_file(path):
    if not os.path.isfile(path):
        return {}

    configuration = None
    with open(path, "r") as configuration_file:
        configuration_file_content = configuration_file.read()
        configuration = json.loads(configuration_file_content)
    return configuration
