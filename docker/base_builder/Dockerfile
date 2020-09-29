FROM debian:buster

# Variable set from CI
ARG GATEWAY_BUILD_SHA1=unset

RUN useradd -ms /bin/bash wirepas

# Install standard tools needed to build transport and sink services
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
       gcc \
       libsystemd-dev \
       make \
       python3-dev \
       python3-gi \
       python3-pip \
    && rm -rf /var/lib/apt/lists/*

USER wirepas

RUN python3 -m pip install wheel setuptools

LABEL com.wirepas.gateway.build.sha1="${GATEWAY_BUILD_SHA1}"
