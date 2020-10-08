FROM wirepas/gateway_base_builder:v1.0 AS builder

COPY --chown=wirepas ./python_transport /home/wirepas/python_transport
WORKDIR /home/wirepas/python_transport

RUN ./utils/generate_wheel.sh

# HACK start: avoid installing grpcio (not needed)
# It should be an option of wirepas-messaging wheel instead

# Install wirepas-messaging manually to avoid installing grpcio
RUN pip3 install protobuf==3.10.0 --user
RUN pip3 install --no-deps wirepas_messaging==1.2.0 --user

# Install manually gateway too to avoid installing grpcio again
# Remove wirepa-messaging from deps
RUN sed -i.bak '/wirepas_messaging/d' requirements.txt
RUN pip3 install -r requirements.txt --no-deps dist/wirepas_gateway*.whl --user

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
