FROM debian:buster-slim AS builder

ARG PROTOBUF_VERSION

RUN useradd -ms /bin/bash wirepas

# Install standard tools needed to build transport and sink services
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
       autoconf \
       automake \
       libtool \
       ca-certificates \
       curl \
       make \
       g++ \
       unzip \
       wget \
       python3 \
       python3-pip \
       python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install wheel setuptools

WORKDIR /home/wirepas

RUN wget https://github.com/protocolbuffers/protobuf/releases/download/v$PROTOBUF_VERSION/protobuf-python-$PROTOBUF_VERSION.tar.gz

RUN tar -xf protobuf-python-$PROTOBUF_VERSION.tar.gz

WORKDIR protobuf-$PROTOBUF_VERSION

# Build the cpp part
RUN ./configure
RUN CXXFLAGS="-fPIC" make -j7
RUN make -j7 check || echo "Errors in check"
RUN make install
RUN ldconfig

RUN protoc --version

# Build the python part
WORKDIR python

RUN python3 setup.py build --cpp_implementation --compile_static_extension
RUN python3 setup.py test --cpp_implementation --compile_static_extension || echo "Errors in python test"
RUN python3 setup.py sdist bdist_wheel --cpp_implementation --compile_static_extension




FROM debian:buster-slim

ARG PROTOBUF_VERSION
# Variable set from CI
ARG GATEWAY_BUILD_SHA1=unset

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
       python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash wirepas

WORKDIR /home/wirepas

COPY --from=builder /home/wirepas/protobuf-$PROTOBUF_VERSION/python/dist/protobuf-$PROTOBUF_VERSION-*.whl .

RUN python3 -m pip install protobuf-$PROTOBUF_VERSION-*.whl

LABEL com.wirepas.gateway.build.sha1="${GATEWAY_BUILD_SHA1}"
