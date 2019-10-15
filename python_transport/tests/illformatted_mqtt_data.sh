#!/usr/bin/env bash

# simple test to test transport mqtt decoding with ill formatted changes

MQTT_HOST=""
MQTT_USER="mqttmasteruser"
MQTT_PWD=""
MQTT_PORT=8883

MQTT_TOPICS=(gw-request/get_configs/23
        \ gw-request/set_config/23/sink0
        \ gw-request/send_data/23/sink0
        \ gw-request/otap_status/23/sink0
        \ gw-request/otap_load_scratchpad/23/sink0
        \ gw-request/otap_process_scratchpad/23/sink0)

for MQTT_TOPIC in ${MQTT_TOPICS[@]}
do

    mosquitto_pub \
         -k 60 \
         -h ${MQTT_HOST} \
         -d \
         -u ${MQTT_USER} \
         -P ${MQTT_PWD} \
         -p ${MQTT_PORT} \
         -t ${MQTT_TOPIC} \
         -m llkaksdklasdk

done
