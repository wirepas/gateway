FROM alpine:3.13 AS builder

# Variable set from CI
ARG GATEWAY_BUILD_SHA1=unset

RUN adduser --disabled-password wirepas

RUN apk add --no-cache gcc make musl-dev elogind-dev python3-dev py3-gobject3 py3-pip

RUN python3 -m pip install wheel setuptools

RUN apk add --no-cache bash

COPY --chown=wirepas ./python_transport /home/wirepas/python_transport
WORKDIR /home/wirepas/python_transport

RUN ./utils/generate_wheel.sh

USER wirepas

RUN pip3 install dist/wirepas_gateway*.whl --user

FROM alpine:3.13

# Variable set from CI
ARG GATEWAY_BUILD_SHA1=unset

RUN adduser --disabled-password wirepas

RUN apk add --no-cache libelogind python3 py3-gobject3 py3-six

USER wirepas

ENV PATH="/home/wirepas/.local/bin:${PATH}"

# Copy the built wheel and its dependencies from builder
COPY --from=builder /home/wirepas/.local /home/wirepas/.local

CMD ["wm-gw"]

LABEL com.wirepas.gateway.build.sha1="${GATEWAY_BUILD_SHA1}"
