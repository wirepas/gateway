FROM alpine:3.12 AS builder

# Variable set from CI
ARG GATEWAY_BUILD_SHA1=unset

RUN apk add --no-cache bash build-base gcc make musl-dev elogind-dev python3-dev git protobuf py3-gobject3 py3-pip linux-headers

RUN pip3 install wheel setuptools

RUN ln -sf /usr/lib/libprotobuf.so.23 /usr/lib/libprotobuf.so

RUN adduser --disabled-password wirepas

USER wirepas

WORKDIR /home/wirepas

# Protobuf
RUN git clone https://github.com/protocolbuffers/protobuf.git
RUN cd protobuf && git checkout v3.12.0
WORKDIR protobuf/python

RUN export LD_LIBRARY_PATH=/usr/lib/

RUN python3 setup.py build --cpp_implementation

# || true as some test are failing on Arm arch
RUN python3 setup.py test --cpp_implementation || true

RUN python3 setup.py clean build install --cpp_implementation --user


# Build sink service
COPY --chown=wirepas ./sink_service /home/wirepas/sink_service
WORKDIR /home/wirepas/sink_service
RUN make

# Transport
COPY --chown=wirepas ./python_transport /home/wirepas/python_transport
WORKDIR /home/wirepas/python_transport

# Remove mesh messaging dep
RUN sed -i.bak '/wirepas_mesh_messaging/d' /home/wirepas/python_transport/requirements.txt
RUN ./utils/generate_wheel.sh

# Install for 3.12
RUN pip3 install --no-deps wirepas_mesh_messaging==1.1.0 --user

RUN pip3 install dist/wirepas_gateway*.whl --user



# Build the final image
FROM alpine:3.12

ARG GATEWAY_BUILD_SHA1=unset

RUN adduser --disabled-password wirepas
RUN addgroup wirepas dialout

RUN apk add --no-cache protobuf libelogind py3-gobject3 dbus py3-six
RUN ln -sf /usr/lib/libprotobuf.so.23 /usr/lib/libprotobuf.so

COPY ./sink_service/com.wirepas.sink.conf /etc/dbus-1/system.d/

COPY ./docker/single_image/launch_script.sh /home/wirepas/launch_script.sh
RUN chmod a+x /home/wirepas/launch_script.sh

USER wirepas

# Copy the built sink-service from builder
COPY --from=builder /home/wirepas/sink_service/build/sinkService /home/wirepas/

# Copy the built wheel and its dependencies from builder
COPY --from=builder /home/wirepas/.local /home/wirepas/.local

ENV PATH="/home/wirepas/.local/bin:${PATH}"

CMD ["sh", "/home/wirepas/launch_script.sh"]

USER root

LABEL com.wirepas.gateway.build.sha1="${GATEWAY_BUILD_SHA1}"
