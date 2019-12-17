import os
import sys
from wirepas_gateway.utils import ParserHelper
from wirepas_gateway import __version__ as transport_version

vars = dict()
vars["WM_SERVICES_MQTT_HOSTNAME"] = "hostname"
vars["WM_SERVICES_MQTT_USERNAME"] = "username"
vars["WM_SERVICES_MQTT_PASSWORD"] = "password"
vars["WM_SERVICES_MQTT_PORT"] = 1998
vars["WM_SERVICES_MQTT_CA_CERTS"] = "path/ca_certs"
vars["WM_SERVICES_MQTT_CLIENT_CRT"] = "path/client_crt"
vars["WM_SERVICES_MQTT_CLIENT_KEY"] = "path/client_key"
vars["WM_SERVICES_MQTT_CIPHERS"] = "path/mqtt_ciphers"

# FALSE, means that we don't set it
vars["WM_SERVICES_MQTT_PERSIST_SESSION"] = True
vars["WM_SERVICES_MQTT_FORCE_UNSECURE"] = True
vars["WM_SERVICES_MQTT_ALLOW_UNTRUSTED"] = True

vars["WM_GW_BUFFERING_MAX_BUFFERED_PACKETS"] = 1000
vars["WM_GW_BUFFERING_MAX_DELAY_WITHOUT_PUBLISH"] = 128
vars["WM_GW_BUFFERING_MINIMAL_SINK_COST"] = 240
vars["WM_GW_ID"] = "1"
vars["WM_GW_MODEL"] = "test"
vars["WM_GW_VERSION"] = "pytest"
vars["WM_GW_IGNORED_ENDPOINTS_FILTER"] = "[10-25,200-220]"
vars["WM_GW_WHITENED_ENDPOINTS_FILTER"] = "[27-30,100-120]"
vars["WM_SERVICES_MQTT_CERT_REQS"] = "CERT_OPTIONAL"
vars["WM_SERVICES_MQTT_TLS_VERSION"] = "PROTOCOL_TLS_SERVER"
vars["WM_SERVICES_MQTT_RECONNECT_DELAY"] = 918

booleans = [
    "WM_SERVICES_MQTT_PERSIST_SESSION",
    "WM_SERVICES_MQTT_FORCE_UNSECURE",
    "WM_SERVICES_MQTT_ALLOW_UNTRUSTED",
]


def get_args(delete_bools=False):

    sys.argv = [sys.argv[0]]

    vcopy = vars.copy()

    if delete_bools:

        for boolean in booleans:
            try:
                del vcopy[boolean]
                del os.environ[boolean]
            except KeyError:
                pass

    for key, value in vcopy.items():
        os.environ[key] = str(value)

    parse = ParserHelper(
        description="Wirepas Gateway Transport service arguments",
        version=transport_version,
    )

    parse.add_file_settings()
    parse.add_mqtt()
    parse.add_gateway_config()
    parse.add_filtering_config()
    parse.add_buffering_settings()

    settings = parse.settings()

    return settings, vcopy


def content_tests(settings, vcopy):

    assert vcopy["WM_SERVICES_MQTT_HOSTNAME"] == settings.mqtt_hostname
    assert vcopy["WM_SERVICES_MQTT_USERNAME"] == settings.mqtt_username
    assert vcopy["WM_SERVICES_MQTT_PASSWORD"] == settings.mqtt_password
    assert vcopy["WM_SERVICES_MQTT_PORT"] == settings.mqtt_port
    assert vcopy["WM_SERVICES_MQTT_CA_CERTS"] == settings.mqtt_ca_certs
    assert vcopy["WM_SERVICES_MQTT_CLIENT_CRT"] == settings.mqtt_certfile
    assert vcopy["WM_SERVICES_MQTT_CLIENT_KEY"] == settings.mqtt_keyfile
    assert vcopy["WM_SERVICES_MQTT_CIPHERS"] == settings.mqtt_ciphers

    if "WM_SERVICES_MQTT_PERSIST_SESSION" not in vcopy:
        assert settings.mqtt_persist_session is False
    else:
        assert (
            vcopy["WM_SERVICES_MQTT_PERSIST_SESSION"] == settings.mqtt_persist_session
        )

    if "WM_SERVICES_MQTT_FORCE_UNSECURE" not in vcopy:
        assert settings.mqtt_force_unsecure is False
    else:
        assert vcopy["WM_SERVICES_MQTT_FORCE_UNSECURE"] == settings.mqtt_force_unsecure

    if "WM_SERVICES_MQTT_ALLOW_UNTRUSTED" not in vcopy:
        assert settings.mqtt_allow_untrusted is False
    else:
        assert (
            vcopy["WM_SERVICES_MQTT_ALLOW_UNTRUSTED"] == settings.mqtt_allow_untrusted
        )

    assert vcopy["WM_SERVICES_MQTT_RECONNECT_DELAY"] == settings.mqtt_reconnect_delay
    assert (
        vcopy["WM_GW_BUFFERING_MAX_BUFFERED_PACKETS"]
        == settings.buffering_max_buffered_packets
    )

    assert (
        vcopy["WM_GW_BUFFERING_MAX_DELAY_WITHOUT_PUBLISH"]
        == settings.buffering_max_delay_without_publish
    )
    assert (
        vcopy["WM_GW_BUFFERING_MINIMAL_SINK_COST"]
        == settings.buffering_minimal_sink_cost
    )

    assert vcopy["WM_GW_ID"] == settings.gateway_id
    assert vcopy["WM_GW_MODEL"] == settings.gateway_model
    assert vcopy["WM_GW_VERSION"] == settings.gateway_version
    assert vcopy["WM_GW_IGNORED_ENDPOINTS_FILTER"] == settings.ignored_endpoints_filter
    assert (
        vcopy["WM_GW_WHITENED_ENDPOINTS_FILTER"] == settings.whitened_endpoints_filter
    )

    assert vcopy["WM_SERVICES_MQTT_CERT_REQS"] == settings.mqtt_cert_reqs
    assert vcopy["WM_SERVICES_MQTT_TLS_VERSION"] == settings.mqtt_tls_version
    assert vcopy["WM_SERVICES_MQTT_RECONNECT_DELAY"] == settings.mqtt_reconnect_delay


def test_argument_env_ingestion():

    settings, vcopy = get_args()
    content_tests(settings, vcopy)


def test_argument_env_ingestion_without_bool():

    settings, vcopy = get_args(delete_bools=True)
    content_tests(settings, vcopy)
