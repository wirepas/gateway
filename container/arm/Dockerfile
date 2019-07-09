# Global arguments
ARG GIT_MANIFEST_FILE=gateway.xml
ARG GIT_MANIFEST_URL=https://github.com/wirepas/manifest.git
ARG GIT_MANIFEST_BRANCH=master

FROM wirepas/base:1.1-raspbian as rpi-builder
RUN [ "cross-build-start" ]

ARG GIT_MANIFEST_FILE
ARG GIT_MANIFEST_URL
ARG GIT_MANIFEST_BRANCH

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
    && echo "LXGW_C_MESH_API_HASH=$(git log -n1 --pretty=%h)" >> /app_build/manifest \
    && make clean \
    && make \
    && echo "LXGW_BUILD=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" >> /app_build/manifest

RUN cd /app_build/python_transport/ \
    && echo "LXGW_SERVICES_HASH=$(git log -n1 --pretty=%h)" >> /app_build/manifest \
    && echo "LXGW_VERSION=$(< wirepas_gateway/__init__.py awk '/__version__/{print $NF}'| tr -d '\"')" >> /app_build/manifest \
    && bash ./utils/generate_wheel.sh

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

COPY --from=rpi-builder /app_build/python_transport/requirements.txt "${TRANSPORT_SERVICE}/"
COPY --from=rpi-builder /app_build/python_transport/dist/* "${TRANSPORT_SERVICE}/"
COPY --from=rpi-builder /app_build/python_transport/wirepas_gateway/wirepas_certs/extwirepas.pem /etc/extwirepas.pem
COPY --from=rpi-builder /app_build/sink_service/build/sinkService /usr/local/bin/sinkService
COPY --from=rpi-builder /app_build/sink_service/com.wirepas.sink.conf /etc/dbus-1/system.d/
COPY --from=rpi-builder /app_build/manifest "${SERVICE_HOME}/manifest"

RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r "${TRANSPORT_SERVICE}/requirements.txt"
RUN pip3 install --no-cache-dir ${WM_TRANSPORT_PKG}

RUN rm -rf "${HOME}/.cache" \
    && chown "${USER}":"${USER}" -R "${HOME}"

COPY --from=rpi-builder /app_build/container/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY --from=rpi-builder /app_build/container/transport.template "${TRANSPORT_SERVICE}/transport.template"

RUN [ "cross-build-end" ]

ARG LXGW_VERSION
ARG BUILD_DATE
ARG IMAGE_NAME
ARG GIT_MANIFEST_FILE
ARG GIT_MANIFEST_URL
ARG GIT_MANIFEST_BRANCH

LABEL com.wirepas.source.manifest="${GIT_MANIFEST_URL}/${GIT_MANIFEST_FILE}#${GIT_MANIFEST_BRANCH}"
LABEL org.opencontainers.image.created=${BUILD_DATE}
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.ref.name=${IMAGE_NAME}
LABEL org.opencontainers.image.schema-version="1.0"
LABEL org.opencontainers.image.title="Wirepas gateway"
LABEL org.opencontainers.image.url="https://github.com/wirepas/gateway"
LABEL org.opencontainers.image.vendor="Wirepas Ltd"
LABEL org.opencontainers.image.version=${LXGW_VERSION}

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["sink"]
