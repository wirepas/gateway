FROM wirepas/base:1.1-ubuntu as builder

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

# builds x86 gateway services
FROM wirepas/base:1.1-ubuntu as wm-lxgw
USER root

ENV SERVICE_HOME="${WM_HOME}"/gateway
ENV SINK_SERVICE="${SERVICE_HOME}"/sink_service
ENV TRANSPORT_SERVICE="${SERVICE_HOME}"/transport_service

ARG WM_TRANSPORT_PKG
ENV WM_TRANSPORT_PKG=${WM_TRANSPORT_PKG:-"${TRANSPORT_SERVICE}/wirepas_gateway-*.tar.gz"}

COPY --from=builder /app_build/python_transport/requirements.txt "${TRANSPORT_SERVICE}"/
COPY --from=builder /app_build/python_transport/dist/* "${TRANSPORT_SERVICE}"/
COPY --from=builder /app_build/python_transport/wirepas_gateway/wirepas_certs/extwirepas.pem /etc/extwirepas.pem
COPY --from=builder /app_build/sink_service/build/sinkService /usr/local/bin/sinkService
COPY --from=builder /app_build/sink_service/com.wirepas.sink.conf /etc/dbus-1/system.d/

RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r "${TRANSPORT_SERVICE}"/requirements.txt
RUN pip3 install --no-cache-dir ${WM_TRANSPORT_PKG}
COPY --from=builder /app_build/container/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY --from=builder /app_build/container/transport.template "${TRANSPORT_SERVICE}/transport.template"
RUN rm -rf "${WM_HOME}"/.cache && chown "${WM_USER}":"${WM_USER}" -R "${WM_HOME}"

ENTRYPOINT ["docker-entrypoint.sh"]
WORKDIR ${WM_HOME}
USER ${WM_USER}
CMD ["sink"]

ARG LXGW_VERSION
LABEL version=${LXGW_VERSION}
