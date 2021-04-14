FROM wirepas/gateway_base_builder:v1.0 AS builder

WORKDIR /home/wirepas

COPY --chown=wirepas ./sink_service /home/wirepas/sink_service

WORKDIR /home/wirepas/sink_service

RUN make

FROM scratch AS export
COPY --from=builder /home/wirepas/sink_service/build/sinkService .

FROM debian:buster-slim

# Variable set from CI
ARG GATEWAY_BUILD_SHA1=unset

RUN useradd -ms /bin/bash wirepas
RUN usermod -a -G dialout wirepas

# Copy the built service and its dependencies from builder
COPY --from=builder /home/wirepas/sink_service/build/sinkService /home/wirepas/

USER wirepas

CMD ["stdbuf", "-oL", "-eL", "/home/wirepas/sinkService"]

LABEL com.wirepas.gateway.build.sha1="${GATEWAY_BUILD_SHA1}"
