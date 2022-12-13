FROM alpine:3.17 AS builder

# Variable set from CI
ARG GATEWAY_BUILD_SHA1=unset

RUN adduser --disabled-password wirepas

RUN apk add --no-cache gcc make musl-dev elogind-dev linux-headers

USER wirepas

LABEL com.wirepas.gateway.build.sha1="${GATEWAY_BUILD_SHA1}"

WORKDIR /home/wirepas

COPY --chown=wirepas ./sink_service /home/wirepas/sink_service

WORKDIR /home/wirepas/sink_service

RUN make

FROM scratch AS export
COPY --from=builder /home/wirepas/sink_service/build/sinkService .

FROM alpine:3.17

# Variable set from CI
ARG GATEWAY_BUILD_SHA1=unset

RUN adduser --disabled-password wirepas
RUN addgroup wirepas dialout

RUN apk add --no-cache libelogind coreutils

# Copy the built service and its dependencies from builder
COPY --from=builder /home/wirepas/sink_service/build/sinkService /home/wirepas/

USER wirepas

CMD ["stdbuf", "-oL", "-eL", "/home/wirepas/sinkService"]

LABEL com.wirepas.gateway.build.sha1="${GATEWAY_BUILD_SHA1}"
