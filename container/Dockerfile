ARG DOCKER_BASE=ubuntu:20.04
ARG CROSS_BUILD_START_CMD=:
ARG CROSS_BUILD_END_CMD=:
ARG LXGW_C_MESH_API_HASH
ARG LXGW_SERVICES_HASH
ARG SOURCE_PATH=.

FROM ${DOCKER_BASE}

RUN ${CROSS_BUILD_START_CMD}
RUN apt-get update  \
    && apt-get install -y \
                       --no-install-recommends \
                       g++ \
                       gcc \
                       gir1.2-gtk-3.0\
                       libsystemd-dev \
                       make \
                       python3 \
                       python3-dev \
                       python3-pip \
                       python3-gi \
                       python3-gi-cairo \
    && rm -rf /var/lib/apt/lists/*

ARG DOCKER_BASE
ARG LXGW_C_MESH_API_HASH
ARG LXGW_SERVICES_HASH
ARG WM_TRANSPORT_PKG

ENV WM_HOME=/home/wirepas
ENV WM_USER=wirepas
ENV SERVICE_HOME="${WM_HOME}/gateway"
ENV TRANSPORT_SERVICE="${SERVICE_HOME}/transport_service"
ENV WM_TRANSPORT_PKG=${WM_TRANSPORT_PKG:-"${TRANSPORT_SERVICE}/wirepas_gateway-*.tar.gz"}

RUN groupadd -r ${WM_USER} --gid 1000 \
    && useradd --uid 1000 -r -g ${WM_USER} ${WM_USER} \
    && mkdir -p ${WM_HOME}

RUN mkdir -vp ${SERVICE_HOME}/ \
    && echo "DOCKER_BASE=${DOCKER_BASE}" > "${SERVICE_HOME}/manifest"

ARG SOURCE_PATH
COPY "${SOURCE_PATH}/sink_service" app_build/sink_service
COPY "${SOURCE_PATH}/python_transport" app_build/python_transport
COPY "${SOURCE_PATH}/container" app_build/container

RUN cp -v /app_build/container/common/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN cd /app_build/python_transport \
    && python3 -m pip install --no-cache-dir --upgrade pip \
    && python3 -m pip install wheel setuptools \
    && ./utils/generate_wheel.sh \
    && mkdir -vp "${TRANSPORT_SERVICE}/" \
    && cp -v /app_build/python_transport/requirements.txt "${TRANSPORT_SERVICE}/" \
    && cp -v /app_build/python_transport/dist/* "${TRANSPORT_SERVICE}/" \
    && echo "LXGW_SERVICES_HASH=${LXGW_SERVICES_HASH}" >> "${SERVICE_HOME}/manifest" \
    && echo "LXGW_VERSION=$(< wirepas_gateway/__about__.py awk '/__version__/{print $NF}'| tr -d '\"')" >> "${SERVICE_HOME}/manifest"

# for caching purposes
RUN python3 -m pip install --no-cache-dir -r "${TRANSPORT_SERVICE}/requirements.txt"
RUN python3 -m pip install --no-cache-dir ${WM_TRANSPORT_PKG}

RUN cd /app_build/sink_service \
    && make \
    && mkdir -vp /etc/dbus-1/system.d/ \
    && mkdir -vp /usr/local/bin/ \
    && cp -v /app_build/sink_service/build/sinkService /usr/local/bin/sinkService \
    && cp -v /app_build/sink_service/com.wirepas.sink.conf /etc/dbus-1/system.d/ \
    && echo "LXGW_BUILD=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"  >> "${SERVICE_HOME}/manifest" \
    && echo "LXGW_C_MESH_API_HASH=${LXGW_C_MESH_API_HASH}" >> "${SERVICE_HOME}/manifest"

RUN rm -rf "${WM_HOME}/.cache" \
    && rm -rf /app_build \
    && chown "${WM_USER}":"${WM_USER}" -R "${WM_HOME}"

ENTRYPOINT ["docker-entrypoint.sh"]
RUN ${CROSS_BUILD_END_CMD}
USER "${WM_USER}"
CMD ["sink"]

ARG BUILD_DATE
ARG IMAGE_NAME
ARG GIT_MANIFEST_FILE
ARG GIT_MANIFEST_URL
ARG GIT_MANIFEST_BRANCH
ARG VERSION
ARG LXGW_C_MESH_API_HASH
ARG LXGW_SERVICES_HASH

LABEL com.wirepas.image.base="${DOCKER_BASE}"
LABEL com.wirepas.source.manifest="${GIT_MANIFEST_URL}/${GIT_MANIFEST_FILE}#${GIT_MANIFEST_BRANCH}"
LABEL com.wirepas.source.cmeshapi="${LXGW_C_MESH_API_HASH}"
LABEL com.wirepas.source.gateway="${LXGW_SERVICES_HASH}"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.ref.name="${IMAGE_NAME}"
LABEL org.opencontainers.image.schema-version="2.0"
LABEL org.opencontainers.image.title="Wirepas gateway"
LABEL org.opencontainers.image.url="https://github.com/wirepas/gateway"
LABEL org.opencontainers.image.vendor="Wirepas Ltd"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
