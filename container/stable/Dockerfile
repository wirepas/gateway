ARG DOCKER_BASE=wirepas/base:1.1-ubuntu
ARG CROSS_BUILD_START_CMD=:
ARG CROSS_BUILD_END_CMD=:
ARG GIT_MANIFEST_FILE=gateway.xml
ARG GIT_MANIFEST_URL=https://github.com/wirepas/manifest.git
ARG GIT_MANIFEST_BRANCH=master

FROM ${DOCKER_BASE} as builder
ARG DOCKER_BASE
ARG GIT_MANIFEST_FILE
ARG GIT_MANIFEST_URL
ARG GIT_MANIFEST_BRANCH
RUN ${CROSS_BUILD_START_CMD}

# install git and initialize repo tool
WORKDIR /app_build

RUN apt-get update  \
    && apt-get install -y --no-install-recommends git curl python ssh \
    && rm -rf /var/lib/apt/lists/*

RUN curl https://storage.googleapis.com/git-repo-downloads/repo > /usr/local/bin/repo \
    && chmod a+x /usr/local/bin/repo \
    && repo init -u ${GIT_MANIFEST_URL} \
                 -m ${GIT_MANIFEST_FILE} \
                 -b ${GIT_MANIFEST_BRANCH} \
                 --no-clone-bundle \
    && repo sync

RUN echo "DOCKER_BASE=${DOCKER_BASE}" >> /app_build/manifest

RUN cd /app_build/sink_service/ \
    && make clean \
    && make \
    && cd c-mesh-api \
    && echo "LXGW_BUILD=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"  >> /app_build/manifest \
    && echo "LXGW_C_MESH_API_HASH=$(git log -n1 --pretty=%h)" >> /app_build/manifest

RUN cd /app_build/python_transport/ \
    && echo "LXGW_SERVICES_HASH=$(git log -n1 --pretty=%h)" >> /app_build/manifest \
    && echo "LXGW_VERSION=$(< wirepas_gateway/__about__.py awk '/__version__/{print $NF}'| tr -d '\"')" >> /app_build/manifest \
    && bash ./utils/generate_wheel.sh



RUN ${CROSS_BUILD_END_CMD}

# builds x86 gateway services
FROM ${DOCKER_BASE} as wm-lxgw
USER root

RUN ${CROSS_BUILD_START_CMD}

ENV SERVICE_HOME="${WM_HOME}/gateway"
ENV SINK_SERVICE="${SERVICE_HOME}/sink_service"
ENV TRANSPORT_SERVICE="${SERVICE_HOME}/transport_service"

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

RUN rm -rf "${WM_HOME}"/.cache && chown "${WM_USER}":"${WM_USER}" -R "${WM_HOME}"
COPY --from=builder /app_build/container/common/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY --from=builder /app_build/container/common/generate_settings.sh "${TRANSPORT_SERVICE}/generate_settings.sh"
COPY --from=builder /app_build/container/common/wm_transport_service.template "${TRANSPORT_SERVICE}/wm_transport_service.template"
RUN ${CROSS_BUILD_END_CMD}

WORKDIR ${WM_HOME}
USER ${WM_USER}

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

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["sink"]
