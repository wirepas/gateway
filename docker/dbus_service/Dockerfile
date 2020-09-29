FROM alpine:3.12.0

# Variable set from CI
ARG GATEWAY_BUILD_SHA1=unset

RUN adduser --disabled-password wirepas

RUN apk add --no-cache dbus

COPY ./sink_service/com.wirepas.sink.conf /etc/dbus-1/system.d/
COPY ./docker/dbus_service/entrypoint.sh /etc/init/

ENTRYPOINT ["/etc/init/entrypoint.sh"]

LABEL com.wirepas.gateway.build.sha1="${GATEWAY_BUILD_SHA1}"
