# Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
#
# See file LICENSE for full license details.
#
BASE_GW_EVENT = "gw-event"
BASE_REQUEST = "gw-request"
BASE_RESPONSE = "gw-response"


class TopicGenerator:
    """
        Static class used as a helper to isolate the mqtt topic part

        It generates string topic from parameters
    """

    @staticmethod
    def _make_topic(base, cmd, params):
        req = base + "/" + cmd

        for param in params:
            req += "/" + param

        return req

    ##################
    # Requests Part
    ##################
    @staticmethod
    def _make_request_topic(cmd, params):
        return TopicGenerator._make_topic(BASE_REQUEST, cmd, params)

    @staticmethod
    def make_get_configs_request_topic(gw_id="+"):
        return TopicGenerator._make_request_topic("get_configs", [str(gw_id)])

    @staticmethod
    def make_set_config_request_topic(gw_id="+", sink_id="+"):
        return TopicGenerator._make_request_topic(
            "set_config", [str(gw_id), str(sink_id)]
        )

    @staticmethod
    def make_send_data_request_topic(gw_id="+", sink_id="+"):
        return TopicGenerator._make_request_topic(
            "send_data", [str(gw_id), str(sink_id)]
        )

    @staticmethod
    def make_otap_status_request_topic(gw_id="+", sink_id="+"):
        return TopicGenerator._make_request_topic(
            "otap_status", [str(gw_id), str(sink_id)]
        )

    @staticmethod
    def make_otap_load_scratchpad_request_topic(gw_id="+", sink_id="+"):
        return TopicGenerator._make_request_topic(
            "otap_load_scratchpad", [str(gw_id), str(sink_id)]
        )

    @staticmethod
    def make_otap_process_scratchpad_request_topic(gw_id="+", sink_id="+"):
        return TopicGenerator._make_request_topic(
            "otap_process_scratchpad", [str(gw_id), str(sink_id)]
        )

    @staticmethod
    def make_otap_set_target_scratchpad_request_topic(gw_id="+", sink_id="+"):
        return TopicGenerator._make_request_topic(
            "otap_set_target_scratchpad", [str(gw_id), str(sink_id)]
        )

    @staticmethod
    def make_get_gateway_info_request_topic(gw_id):
        return TopicGenerator._make_request_topic("get_gw_info", [str(gw_id)])

    ##################
    # Response Part
    ##################
    @staticmethod
    def _make_response_topic(cmd, params):
        return TopicGenerator._make_topic(BASE_RESPONSE, cmd, params)

    @staticmethod
    def make_get_configs_response_topic(gw_id="+"):
        return TopicGenerator._make_response_topic("get_configs", [str(gw_id)])

    @staticmethod
    def make_set_config_response_topic(gw_id, sink_id):
        return TopicGenerator._make_response_topic(
            "set_config", [str(gw_id), str(sink_id)]
        )

    @staticmethod
    def make_send_data_response_topic(gw_id, sink_id):
        return TopicGenerator._make_response_topic(
            "send_data", [str(gw_id), str(sink_id)]
        )

    @staticmethod
    def make_otap_status_response_topic(gw_id="+", sink_id="+"):
        return TopicGenerator._make_response_topic(
            "otap_status", [str(gw_id), str(sink_id)]
        )

    @staticmethod
    def make_otap_upload_scratchpad_response_topic(gw_id="+", sink_id="+"):
        return TopicGenerator._make_response_topic(
            "otap_load_scratchpad", [str(gw_id), str(sink_id)]
        )

    @staticmethod
    def make_otap_process_scratchpad_response_topic(gw_id="+", sink_id="+"):
        return TopicGenerator._make_response_topic(
            "otap_process_scratchpad", [str(gw_id), str(sink_id)]
        )

    @staticmethod
    def make_otap_set_target_scratchpad_response_topic(gw_id="+", sink_id="+"):
        return TopicGenerator._make_response_topic(
            "otap_set_target_scratchpad", [str(gw_id), str(sink_id)]
        )

    @staticmethod
    def make_get_gateway_info_response_topic(gw_id):
        return TopicGenerator._make_response_topic("get_gw_info", [str(gw_id)])

    ##################
    # Event Part
    ##################
    @staticmethod
    def _make_event_topic(cmd, params):
        return TopicGenerator._make_topic(BASE_GW_EVENT, cmd, params)

    @staticmethod
    def make_status_topic(gw_id="+"):
        return TopicGenerator._make_event_topic("status", [str(gw_id)])

    @staticmethod
    def make_received_data_topic(
        gw_id="+", sink_id="+", network_id="+", src_ep="+", dst_ep="+"
    ):
        return TopicGenerator._make_event_topic(
            "received_data",
            [str(gw_id), str(sink_id), str(network_id), str(src_ep), str(dst_ep)],
        )


class TopicParser:
    """
        Static class used as a helper to parse topic

        It parses parameters from topic string topic
        """

    @staticmethod
    def parse_send_data_topic(topic):
        _, cmd, gw_id, sink_id = topic.split("/")
        if not cmd.startswith("send_data"):
            raise RuntimeError("Wrong topic for send_data_request")

        return gw_id, sink_id
