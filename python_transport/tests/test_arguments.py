import os
import sys
import yaml
from wirepas_gateway.utils import ParserHelper
from wirepas_gateway import __version__ as transport_version

env_vars = dict()
env_vars["WM_SERVICES_MQTT_HOSTNAME"] = "hostname"
env_vars["WM_SERVICES_MQTT_USERNAME"] = "username"
env_vars["WM_SERVICES_MQTT_PASSWORD"] = "password"
env_vars["WM_SERVICES_MQTT_PORT"] = 19723788
env_vars["WM_SERVICES_MQTT_CA_CERTS"] = "path/ca_certs"
env_vars["WM_SERVICES_MQTT_CLIENT_CRT"] = "path/client_crt"
env_vars["WM_SERVICES_MQTT_CLIENT_KEY"] = "path/client_key"
env_vars["WM_SERVICES_MQTT_CIPHERS"] = "path/mqtt_ciphers"

# FALSE, means that we don't set it
env_vars["WM_SERVICES_MQTT_PERSIST_SESSION"] = True
env_vars["WM_SERVICES_MQTT_FORCE_UNSECURE"] = True
env_vars["WM_SERVICES_MQTT_ALLOW_UNTRUSTED"] = True

env_vars["WM_GW_BUFFERING_MAX_BUFFERED_PACKETS"] = 1000
env_vars["WM_GW_BUFFERING_MAX_DELAY_WITHOUT_PUBLISH"] = 128
env_vars["WM_GW_BUFFERING_MINIMAL_SINK_COST"] = 240
env_vars["WM_GW_ID"] = "1"
env_vars["WM_GW_MODEL"] = "test"
env_vars["WM_GW_VERSION"] = "pytest"
env_vars["WM_GW_IGNORED_ENDPOINTS_FILTER"] = "[10-25,200-220]"
env_vars["WM_GW_WHITENED_ENDPOINTS_FILTER"] = "[27-30,100-120]"
env_vars["WM_SERVICES_MQTT_CERT_REQS"] = "CERT_OPTIONAL"
env_vars["WM_SERVICES_MQTT_TLS_VERSION"] = "PROTOCOL_TLS_SERVER"
env_vars["WM_SERVICES_MQTT_RECONNECT_DELAY"] = 918

file_vars = dict()
file_vars["settings"] = "./test.yaml"
file_vars["mqtt_hostname"] = env_vars["WM_SERVICES_MQTT_HOSTNAME"]
file_vars["mqtt_username"] = env_vars["WM_SERVICES_MQTT_USERNAME"]
file_vars["mqtt_password"] = env_vars["WM_SERVICES_MQTT_PASSWORD"]
file_vars["mqtt_port"] = env_vars["WM_SERVICES_MQTT_PORT"]
file_vars["mqtt_ca_certs"] = env_vars["WM_SERVICES_MQTT_CA_CERTS"]
file_vars["mqtt_keyfile"] = env_vars["WM_SERVICES_MQTT_CLIENT_KEY"]
file_vars["mqtt_cert_reqs"] = env_vars["WM_SERVICES_MQTT_CERT_REQS"]
file_vars["mqtt_tls_version"] = env_vars["WM_SERVICES_MQTT_TLS_VERSION"]
file_vars["mqtt_certfile"] = env_vars["WM_SERVICES_MQTT_CLIENT_CRT"]
file_vars["mqtt_ciphers"] = env_vars["WM_SERVICES_MQTT_CIPHERS"]
file_vars["mqtt_persist_session"] = env_vars["WM_SERVICES_MQTT_PERSIST_SESSION"]
file_vars["mqtt_force_unsecure"] = env_vars["WM_SERVICES_MQTT_FORCE_UNSECURE"]
file_vars["mqtt_allow_untrusted"] = env_vars["WM_SERVICES_MQTT_ALLOW_UNTRUSTED"]
file_vars["mqtt_reconnect_delay"] = env_vars["WM_SERVICES_MQTT_RECONNECT_DELAY"]
file_vars["buffering_max_buffered_packets"] = env_vars[
    "WM_GW_BUFFERING_MAX_BUFFERED_PACKETS"
]
file_vars["buffering_max_delay_without_publish"] = env_vars[
    "WM_GW_BUFFERING_MAX_DELAY_WITHOUT_PUBLISH"
]
file_vars["buffering_minimal_sink_cost"] = env_vars["WM_GW_BUFFERING_MINIMAL_SINK_COST"]

file_vars["gateway_id"] = env_vars["WM_GW_ID"]
file_vars["gateway_model"] = env_vars["WM_GW_MODEL"]
file_vars["gateway_version"] = env_vars["WM_GW_VERSION"]
file_vars["ignored_endpoints_filter"] = env_vars["WM_GW_IGNORED_ENDPOINTS_FILTER"]
file_vars["whitened_endpoints_filter"] = env_vars["WM_GW_WHITENED_ENDPOINTS_FILTER"]

booleans = [
    "WM_SERVICES_MQTT_PERSIST_SESSION",
    "WM_SERVICES_MQTT_FORCE_UNSECURE",
    "WM_SERVICES_MQTT_ALLOW_UNTRUSTED",
]


def get_args(delete_bools=False, set_env=True, set_file=False):

    sys.argv = [sys.argv[0]]
    vcopy = env_vars.copy()

    if set_env:
        if delete_bools:

            for boolean in booleans:
                try:
                    del vcopy[boolean]
                    del os.environ[boolean]
                except KeyError:
                    pass

        for key, value in vcopy.items():
            os.environ[key] = str(value)

    if set_file:
        filename = "test.yaml"
        with open(filename, "w") as fp:
            yaml.dump(file_vars, fp)
        sys.argv.append("--settings")
        sys.argv.append(filename)

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


def test_defaults():
    """
    Tests a few of the critical default values such as port number.
    The goal is to ensure that the custom type does no interfere with the
    acquisition.
    """

    parse = ParserHelper(
        description="Wirepas Gateway Transport service arguments",
        version=transport_version,
    )

    parse.add_file_settings()
    parse.add_mqtt()
    parse.add_gateway_config()
    parse.add_filtering_config()
    parse.add_buffering_settings()

    sys.argv = [sys.argv[0]]
    settings = parse.settings()

    assert settings.mqtt_hostname is None
    assert settings.mqtt_username is None
    assert settings.mqtt_password is None
    assert settings.mqtt_port == 8883
    assert settings.mqtt_ca_certs is None
    assert settings.mqtt_certfile is None
    assert settings.mqtt_keyfile is None
    assert settings.mqtt_ciphers is None
    assert settings.mqtt_persist_session is False
    assert settings.mqtt_force_unsecure is False
    assert settings.mqtt_allow_untrusted is False
    assert settings.mqtt_reconnect_delay == 0
    assert settings.buffering_max_buffered_packets == 0
    assert settings.buffering_max_delay_without_publish == 0
    assert settings.buffering_minimal_sink_cost == 0
    assert settings.gateway_id is None
    assert settings.gateway_model is None
    assert settings.gateway_version is None
    assert settings.ignored_endpoints_filter is None
    assert settings.whitened_endpoints_filter is None
    assert settings.mqtt_cert_reqs == "CERT_REQUIRED"
    assert settings.mqtt_tls_version == "PROTOCOL_TLSv1_2"


def test_type_conversion():
    """
    Ensures that int, str and boolean conversion works as expected.
    """

    os.environ["WM_GW_ID"] = ""
    os.environ["WM_SERVICES_MQTT_HOSTNAME"] = ""
    os.environ["WM_SERVICES_MQTT_PERSIST_SESSION"] = ""
    os.environ["WM_SERVICES_MQTT_RECONNECT_DELAY"] = "0111"
    sys.argv = [sys.argv[0]]

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

    assert settings.gateway_id is None
    assert settings.mqtt_hostname is None
    assert settings.mqtt_persist_session is False
    assert settings.mqtt_reconnect_delay == 111


def test_argument_file_ingestion():

    settings, vcopy = get_args(delete_bools=False, set_env=False, set_file=True)
    content_tests(settings, vcopy)


def test_argument_env_ingestion():

    settings, vcopy = get_args()
    content_tests(settings, vcopy)


def test_argument_env_ingestion_without_bool():

    settings, vcopy = get_args(delete_bools=True, set_env=True, set_file=False)
    content_tests(settings, vcopy)
