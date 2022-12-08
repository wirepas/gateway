FROM python:3.10.8-alpine3.17 AS builder

RUN adduser --disabled-password wirepas

RUN apk add --no-cache \
		gcc \
		bash \
		build-base \
		make \
		musl-dev \
		elogind-dev \
		python3-dev \
		py3-gobject3 \
		cairo-dev \
		gobject-introspection-dev

RUN python3 -m pip install wheel setuptools pkgconfig

USER wirepas
WORKDIR /home/wirepas

COPY --chown=wirepas ./python_transport /home/wirepas/python_transport
WORKDIR /home/wirepas/python_transport

RUN ./utils/generate_wheel.sh

USER wirepas

# Note:
# We are re-using the transport service module builder for the dbus client.
# This is a hack as dbus client is part of python_transport.
# But, they should be splitted later and the dbus client wheel
# will be independent from the transport service.

RUN pip3 install dist/wirepas_gateway*.whl --no-deps --user
# Dependencies are installed manually as runner image already have wmm
# Todo: removing wmm from requirement list would be better
RUN pip3 install pydbus==0.6.0 PyYAML==6.0.1 --user
RUN pip3 install gobject PyGObject --user
RUN pip3 install ntplib --user


# Build the final image with prebuilt wmm image
FROM wirepas/wmm_alpine_cpp:1.2.5

USER root

# Variable set from CI
ARG GATEWAY_BUILD_SHA1=unset

RUN apk add --no-cache libelogind glib gobject-introspection

USER wirepas

ENV PATH="/home/wirepas/.local/bin:${PATH}"

# Copy the built wheel and its dependencies from builder
COPY --from=builder /home/wirepas/.local /home/wirepas/.local

COPY ./rtc_service/*.py /home/wirepas/rtc_service/

CMD ["python3", "/home/wirepas/rtc_service/rtc_service.py"]

LABEL com.wirepas.gateway.build.sha1="${GATEWAY_BUILD_SHA1}"
