# Duplicate of transport service for now
FROM python:3.8.8-alpine3.12 AS builder

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

RUN pip3 install dist/wirepas_gateway*.whl --no-deps --user

RUN pip3 install pydbus==0.6.0 PyYAML==5.4 --user
RUN pip3 install gobject PyGObject --user


# Build the final image
#FROM python:3.8.8-alpine3.12 as runner
FROM wirepas/wmm_alpine_cpp:1.2 as runner

USER root

# Variable set from CI
ARG GATEWAY_BUILD_SHA1=unset

RUN apk add --no-cache libelogind glib gobject-introspection ndisc6 iproute2 sudo

RUN adduser wirepas wheel

# Allow wirepas user to execute some commands with sudo power without password
COPY ./ipv6_service/wirepas_sudo_rights /etc/sudoers.d/

USER wirepas

ENV PATH="/home/wirepas/.local/bin:${PATH}"

# Copy the built wheel and its dependencies from builder
COPY --from=builder /home/wirepas/.local /home/wirepas/.local

COPY ./ipv6_service/ipv6_service.py /home/wirepas/ipv6/

CMD ["python3", "/home/wirepas/ipv6/ipv6_service.py"]

LABEL com.wirepas.gateway.build.sha1="${GATEWAY_BUILD_SHA1}"
