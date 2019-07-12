FROM wirepas/base:1.1-ubuntu as builder

COPY sink_service app_build/sink_service
COPY python_transport app_build/python_transport
COPY container app_build/container

WORKDIR /app_build
RUN cd /app_build/sink_service/ \
    && make clean \
    && make \
    && echo "LXGW_BUILD=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"  >> /app_build/manifest

RUN cd /app_build/python_transport/ \
    && ./utils/generate_wheel.sh

# builds x86 gateway services
FROM wirepas/base:1.1-ubuntu as wm-lxgw
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
COPY --from=builder /app_build/container/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY --from=builder /app_build/container/transport.template "${TRANSPORT_SERVICE}/transport.template"
RUN rm -rf "${WM_HOME}/.cache" \
    && chown "${WM_USER}":"${WM_USER}" -R "${WM_HOME}"

ENTRYPOINT ["docker-entrypoint.sh"]
WORKDIR ${WM_HOME}
USER ${WM_USER}
CMD ["sink"]

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
