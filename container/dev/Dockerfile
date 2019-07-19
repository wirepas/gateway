ARG DOCKER_BASE=wirepas/base:1.1-ubuntu
ARG CROSS_BUILD_START_CMD=:
ARG CROSS_BUILD_END_CMD=:
ARG LXGW_C_MESH_API_HASH
ARG LXGW_SERVICES_HASH

FROM ${DOCKER_BASE} as builder

ARG DOCKER_BASE
ARG LXGW_C_MESH_API_HASH
ARG LXGW_SERVICES_HASH

RUN ${CROSS_BUILD_START_CMD}

COPY sink_service app_build/sink_service
COPY python_transport app_build/python_transport
COPY container app_build/container

RUN echo "DOCKER_BASE=${DOCKER_BASE}" >> /app_build/manifest
RUN cd /app_build/python_transport \
    && ./utils/generate_wheel.sh \
    && echo "LXGW_SERVICES_HASH=${LXGW_SERVICES_HASH}" >> /app_build/manifest \
    && echo "LXGW_VERSION=$(< wirepas_gateway/__about__.py awk '/__version__/{print $NF}'| tr -d '\"')" >> /app_build/manifest

RUN cd /app_build/sink_service \
    && make clean \
    && make \
    && echo "LXGW_BUILD=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"  >> /app_build/manifest \
    && echo "LXGW_C_MESH_API_HASH=${LXGW_C_MESH_API_HASH}" >> /app_build/manifest


RUN ${CROSS_BUILD_END_CMD}

FROM ${DOCKER_BASE} as wm-lxgw
RUN ${CROSS_BUILD_START_CMD}
USER root

ENV SERVICE_HOME="${WM_HOME}"/gateway
ENV SINK_SERVICE="${SERVICE_HOME}"/sink_service
ENV TRANSPORT_SERVICE="${SERVICE_HOME}"/transport_service

ARG WM_TRANSPORT_PKG
ENV WM_TRANSPORT_PKG=${WM_TRANSPORT_PKG:-"${TRANSPORT_SERVICE}/wirepas_gateway-*.tar.gz"}

COPY --from=builder /app_build/python_transport/requirements.txt "${TRANSPORT_SERVICE}/"
COPY --from=builder /app_build/python_transport/dist/* "${TRANSPORT_SERVICE}/"
COPY --from=builder /app_build/python_transport/wirepas_gateway/wirepas_certs/extwirepas.pem /etc/extwirepas.pem
COPY --from=builder /app_build/sink_service/build/sinkService /usr/local/bin/sinkService
COPY --from=builder /app_build/sink_service/com.wirepas.sink.conf /etc/dbus-1/system.d/
COPY --from=builder /app_build/manifest "${SERVICE_HOME}/manifest"

RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r "${TRANSPORT_SERVICE}/requirements.txt"
RUN pip3 install --no-cache-dir ${WM_TRANSPORT_PKG}
COPY --from=builder /app_build/container/common/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY --from=builder /app_build/container/common/generate_settings.sh "${TRANSPORT_SERVICE}/generate_settings.sh"
COPY --from=builder /app_build/container/common/wm_transport_service.template "${TRANSPORT_SERVICE}/wm_transport_service.template"
RUN rm -rf "${WM_HOME}/.cache" \
    && chown "${WM_USER}":"${WM_USER}" -R "${WM_HOME}"

ENTRYPOINT ["docker-entrypoint.sh"]
WORKDIR ${WM_HOME}
RUN ${CROSS_BUILD_END_CMD}
USER ${WM_USER}
CMD ["sink"]

ARG BUILD_DATE
ARG DOCKER_BASE
ARG IMAGE_NAME
ARG GIT_MANIFEST_FILE
ARG GIT_MANIFEST_URL
ARG GIT_MANIFEST_BRANCH
ARG VERSION

LABEL com.wirepas.image.base="${DOCKER_BASE}"
LABEL com.wirepas.source.manifest="${GIT_MANIFEST_URL}/${GIT_MANIFEST_FILE}#${GIT_MANIFEST_BRANCH}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.ref.name="${IMAGE_NAME}"
LABEL org.opencontainers.image.schema-version="1.0"
LABEL org.opencontainers.image.title="Wirepas gateway"
LABEL org.opencontainers.image.url="https://github.com/wirepas/gateway"
LABEL org.opencontainers.image.vendor="Wirepas Ltd"
LABEL org.opencontainers.image.version="${VERSION}"
