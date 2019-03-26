# Wirepas Oy

# Builds wirepas messaging
FROM wirepas-base:1.0 as messaging-builder
ENV PACKAGE_PATH=public-apis/python
WORKDIR /app_build

COPY ${PACKAGE_PATH}/requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY ${PACKAGE_PATH}/ .
RUN ./utils/compile_protos.sh
RUN py3clean . || true \
    && python3 setup.py clean --all \
    && python3 setup.py sdist bdist_wheel
RUN ls dist/

# Builds sink service
FROM wirepas-base:1.0 as wm-sink-service-builder
ENV PACKAGE_PATH=sink_service
WORKDIR /app_build

COPY ${PACKAGE_PATH}/ .
RUN make clean && make

# Builds transport service
FROM wirepas-base:1.0 as wm-transport-service-builder
ENV PACKAGE_PATH=python_transport
WORKDIR /app_build

COPY ${PACKAGE_PATH}/requirements.txt requirements.txt
COPY ${PACKAGE_PATH}/ .
RUN py3clean . || true \
    && python3 setup.py clean --all \
    && python3 setup.py sdist bdist_wheel

RUN pip install Sphinx \
    && pip install sphinxcontrib-napoleon \
    && ./utils/generate_sphinx_docs.sh
RUN ls dist/



# builds x86 gateway services
FROM wirepas-base:1.0 as wm-lxgw
USER root

ARG WM_MESSAGING_PKG
ENV WM_MESSAGING_PKG=${WM_MESSAGING_PKG:-"wirepas_messaging-*.tar*"}

ARG WM_TRANSPORT_PKG
ENV WM_TRANSPORT_PKG=${WM_TRANSPORT_PKG:-"wirepas_gateway-*.tar*"}

ENV SERVICE_HOME=${HOME}/gateway
ENV SINK_SERVICE=${SERVICE_HOME}/sink_service
ENV TRANSPORT_SERVICE=${SERVICE_HOME}/transport_service

COPY --from=messaging-builder /app_build/dist/${WM_MESSAGING_PKG} ${HOME}/dependencies/
COPY --from=wm-sink-service-builder /app_build/build/sinkService /usr/local/bin/sinkService
COPY --from=wm-transport-service-builder /app_build/dist/${WM_TRANSPORT_PKG} ${TRANSPORT_SERVICE}/
COPY --from=wm-transport-service-builder /app_build/docs/ ${TRANSPORT_SERVICE}/docs

WORKDIR ${HOME}
RUN pip3 install ${HOME}/dependencies/${WM_MESSAGING_PKG}
RUN pip3 install ${TRANSPORT_SERVICE}/${WM_TRANSPORT_PKG}

COPY python_transport/wirepas_gateway/wirepas_certs/extwirepas.pem /etc/extwirepas.pem
COPY sink_service/com.wirepas.sink.conf /etc/dbus-1/system.d/

RUN chown ${USER}:${USER} -R ${HOME} \
    && rm -rf ${HOME}/.cache

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

COPY container/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN ln -s usr/local/bin/docker-entrypoint.sh / # backwards compat
ENTRYPOINT ["docker-entrypoint.sh"]

USER ${USER}
CMD ["sink"]


# Builds transport service
FROM wirepas-base-rpi:1.0 as wm-transport-service-builder-rpi
RUN [ "cross-build-start" ]
ENV PACKAGE_PATH=python_transport
WORKDIR /app_build

COPY ${PACKAGE_PATH}/requirements.txt requirements.txt
#RUN pip3 install -r requirements.txt
COPY ${PACKAGE_PATH}/ .
RUN py3clean . || true \
    && python3 setup.py clean --all \
    && python3 setup.py sdist bdist_wheel
RUN [ "cross-build-end" ]
#RUN ./utils/generate_sphinx_docs.sh

# !!! Assuming the wheels are universal !!!
# Builds sink service
FROM wirepas-base-rpi:1.0 as wm-sink-service-builder-rpi
RUN [ "cross-build-start" ]
ENV PACKAGE_PATH=sink_service
WORKDIR /app_build
COPY ${PACKAGE_PATH}/ .
RUN make clean && make
RUN [ "cross-build-end" ]


FROM wirepas-base-rpi:1.0 as wm-lxgw-rpi
RUN [ "cross-build-start" ]

USER root
RUN apt-get update && apt-get install --no-install-recommends python3-gi-cairo

ENV SERVICE_HOME=${HOME}/gateway
ENV SINK_SERVICE=${SERVICE_HOME}/sink_service
ENV TRANSPORT_SERVICE=${SERVICE_HOME}/transport_service

ARG WM_MESSAGING_PKG
ENV WM_MESSAGING_PKG=${WM_MESSAGING_PKG:-"wirepas_messaging-*.tar*"}

ARG WM_TRANSPORT_PKG
ENV WM_TRANSPORT_PKG=${WM_TRANSPORT_PKG:-"wirepas_gateway-*.tar*"}

COPY --from=messaging-builder /app_build/dist/${WM_MESSAGING_PKG} ${HOME}/dependencies/
COPY --from=wm-sink-service-builder-rpi /app_build/build/sinkService /usr/local/bin/sinkService
COPY --from=wm-transport-service-builder-rpi /app_build/dist/${WM_TRANSPORT_PKG} ${TRANSPORT_SERVICE}/

RUN pip3 install ${HOME}/dependencies/${WM_MESSAGING_PKG}
RUN pip3 install ${TRANSPORT_SERVICE}/${WM_TRANSPORT_PKG}

COPY python_transport/wirepas_gateway/wirepas_certs/extwirepas.pem /etc/extwirepas.pem
COPY sink_service/com.wirepas.sink.conf /etc/dbus-1/system.d/

# Environment
ARG WM_SERVICES_HOST
ARG WM_SERVICES_MQTT_PORT
ARG WM_SERVICES_MQTT_USER
ARG WM_SERVICES_MQTT_PASSWORD
ARG WM_SERVICES_CERTIFICATE_CHAIN
ARG WM_SERVICES_GATEWAY_ID

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

COPY container/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN ln -s usr/local/bin/docker-entrypoint.sh / # backwards compat
ENTRYPOINT ["docker-entrypoint.sh"]

RUN chown ${USER}:${USER} -R ${HOME} \
    && rm -rf ${HOME}/.cache

RUN [ "cross-build-end" ]
USER ${USER}
CMD ["sink"]

