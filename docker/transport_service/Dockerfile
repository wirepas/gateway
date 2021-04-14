FROM wirepas/gateway_base_builder:v1.0 AS builder

COPY --chown=wirepas ./python_transport /home/wirepas/python_transport
WORKDIR /home/wirepas/python_transport

RUN ./utils/generate_wheel.sh

RUN pip3 install dist/wirepas_gateway*.whl --user

FROM scratch AS export
COPY --from=builder /home/wirepas/python_transport/dist/*.tar.gz .

FROM debian:buster-slim

# Variable set from CI
ARG GATEWAY_BUILD_SHA1=unset

RUN useradd -ms /bin/bash wirepas

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
       ca-certificates \
       python3-gi \
    && rm -rf /var/lib/apt/lists/*

RUN c_rehash -v /etc/ssl/certs/

USER wirepas

ENV PATH="/home/wirepas/.local/bin:${PATH}"

# Copy the built wheel and its dependencies from builder
COPY --from=builder /home/wirepas/.local /home/wirepas/.local

CMD ["wm-gw"]

LABEL com.wirepas.gateway.build.sha1="${GATEWAY_BUILD_SHA1}"
