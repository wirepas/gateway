FROM wirepas/base:1.1-raspbian as rpi-builder
RUN [ "cross-build-start" ]

ARG GIT_MANIFEST_FILE
ARG GIT_MANIFEST_URL

ENV GIT_MANIFEST_FILE=${GIT_MANIFEST_FILE:-"gateway.xml"}
ENV GIT_MANIFEST_URL=${GIT_MANIFEST_URL:-"https://github.com/wirepas/manifest.git"}

# install git and initialize repo tool
WORKDIR /app_build
RUN apt-get update  \
    && apt-get install -y --no-install-recommends git curl python ssh \
    && rm -rf /var/lib/apt/lists/* \
    && curl https://storage.googleapis.com/git-repo-downloads/repo > /usr/local/bin/repo \
    && chmod a+x /usr/local/bin/repo \
    && repo init -u ${GIT_MANIFEST_URL} \
                 -m ${GIT_MANIFEST_FILE} \
                 --no-clone-bundle \
    && repo sync

RUN cd /app_build/sink_service/ \
    && make clean \
    && make

RUN cd /app_build/python_transport/ \
    && ./utils/generate_wheel.sh

RUN [ "cross-build-end" ]

# builds final image
FROM wirepas/base:1.1-raspbian as wm-lxgw
RUN [ "cross-build-start" ]
USER root

ENV SERVICE_HOME="${HOME}/gateway"
ENV SINK_SERVICE="${SERVICE_HOME}/sink_service"
ENV TRANSPORT_SERVICE="${SERVICE_HOME}/transport_service"
ARG WM_TRANSPORT_PKG
ENV WM_TRANSPORT_PKG=${WM_TRANSPORT_PKG:-"${TRANSPORT_SERVICE}/wirepas_gateway-*.tar.gz"}

COPY --from=rpi-builder /app_build/gateway/python_transport/requirements.txt "${TRANSPORT_SERVICE}"/
COPY --from=rpi-builder /app_build/gateway/python_transport/dist/* "${TRANSPORT_SERVICE}"/
COPY --from=rpi-builder /app_build/gateway/python_transport/wirepas_gateway/wirepas_certs/extwirepas.pem /etc/extwirepas.pem
COPY --from=rpi-builder /app_build/gateway/sink_service/build/sinkService /usr/local/bin/sinkService
COPY --from=rpi-builder /app_build/gateway/sink_service/com.wirepas.sink.conf /etc/dbus-1/system.d/

RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r "${TRANSPORT_SERVICE}"/requirements.txt
RUN pip3 install --no-cache-dir ${WM_TRANSPORT_PKG}

RUN rm -rf "${HOME}"/.cache \
    && chown "${USER}":"${USER}" -R "${HOME}"

COPY --from=rpi-builder /app_build/gateway/container/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

CMD ["sink"]
RUN [ "cross-build-end" ]

ARG LXGW_VERSION
LABEL version=${LXGW_VERSION}
