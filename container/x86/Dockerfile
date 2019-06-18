FROM wirepas/base:1.1-ubuntu as builder

ARG GIT_TAG=${GIT_TAG:-"master"}

# Update the sources list
RUN apt-get update  \
    && apt-get install -y  --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app_build
ENV SINK_SERVICE="/app_build/gateway/sink_service/"
ENV TRANSPORT_SERVICE="/app_build/gateway/python_transport/"

RUN git clone --branch "${GIT_TAG}" https://github.com/wirepas/gateway.git gateway
RUN git clone --branch "${GIT_TAG}" https://github.com/wirepas/c-mesh-api.git gateway/sink_service/c-mesh-api

RUN cd "${SINK_SERVICE}" \
    && make clean \
    && make

RUN cd "${TRANSPORT_SERVICE}" \
    && ./utils/generate_wheel.sh

# builds x86 gateway services
FROM wirepas/base:1.1-ubuntu as wm-lxgw
USER root

ENV SERVICE_HOME="${HOME}"/gateway
ENV SINK_SERVICE="${SERVICE_HOME}"/sink_service
ENV TRANSPORT_SERVICE="${SERVICE_HOME}"/transport_service
ARG WM_TRANSPORT_PKG
ENV WM_TRANSPORT_PKG=${WM_TRANSPORT_PKG:-"${TRANSPORT_SERVICE}/wirepas_gateway-*.tar.gz"}

COPY --from=builder /app_build/gateway/python_transport/requirements.txt "${TRANSPORT_SERVICE}"/
COPY --from=builder /app_build/gateway/python_transport/dist/* "${TRANSPORT_SERVICE}"/
COPY --from=builder /app_build/gateway/python_transport/wirepas_gateway/wirepas_certs/extwirepas.pem /etc/extwirepas.pem
COPY --from=builder /app_build/gateway/sink_service/build/sinkService /usr/local/bin/sinkService
COPY --from=builder /app_build/gateway/sink_service/com.wirepas.sink.conf /etc/dbus-1/system.d/

RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r "${TRANSPORT_SERVICE}"/requirements.txt
RUN pip3 install --no-cache-dir ${WM_TRANSPORT_PKG}

RUN rm -rf "${HOME}"/.cache \
    && chown "${USER}":"${USER}" -R "${HOME}"

# Environment
ARG WM_SERVICES_HOST
ARG WM_SERVICES_MQTT_PORT
ARG WM_SERVICES_MQTT_USER
ARG WM_SERVICES_MQTT_PASSWORD
ARG WM_SERVICES_CERTIFICATE_CHAIN

ARG WM_SINK_UART_PORT
ARG WM_SINK_UART_BITRATE
ARG WM_SINK_ID

ENV WM_SERVICES_HOST=${WM_SERVICES_HOST:-"localhost"}
ENV WM_SERVICES_MQTT_PORT=${WM_SERVICES_MQTT_PORT:-"1883"}
ENV WM_SERVICES_MQTT_USER=${WM_SERVICES_MQTT_USER:-"mqttuser"}
ENV WM_SERVICES_MQTT_PASSWORD=${WM_SERVICES_MQTT_PASSWORD:-"12sdftat3089ajoiausd+91as12"}
ENV WM_SERVICES_CERTIFICATE_CHAIN=${WM_SERVICES_CERTIFICATE_CHAIN:-""}
ENV WM_SERVICES_GATEWAY_ID=${WM_SERVICES_GATEWAY_ID:-""}

ENV WM_SINK_UART_PORT=${WM_SINK_UART_PORT:-"/dev/ttyACM0"}
ENV WM_SINK_UART_BITRATE={WM_SINK_UART_BITRATE:-"125000"}
ENV WM_SINK_ID=${WM_SINK_ID:-"0"}

ENV EXEC_TRANSPORT "wm-gw"
ENV EXEC_SINK /usr/local/bin/sinkService

COPY --from=builder /app_build/gateway/container/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

CMD ["sink"]
