# Duplicate of transport service for now
FROM python:3.10.8-alpine3.17 AS builder

RUN adduser --disabled-password wirepas

RUN apk add --no-cache \
		gcc \
		bash \
		build-base \
		make \
		cmake \
		musl-dev \
		dpkg \
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

RUN pip3 install pydbus==0.6.0 PyYAML==6.0.1 --user
RUN pip3 install gobject==0.1.0 PyGObject==3.46.0 --user


# Build the final image
FROM wirepas/wmm_alpine_cpp:1.2.5 as runner

USER root

# Variable set from CI
ARG GATEWAY_BUILD_SHA1=unset

RUN apk add --no-cache libelogind glib gobject-introspection

USER wirepas

ENV PATH="/home/wirepas/.local/bin:${PATH}"

# Copy the built wheel and its dependencies from builder
COPY --from=builder /home/wirepas/.local /home/wirepas/.local

COPY ./local_history_service/*.py /home/wirepas/local_history_service/

CMD ["python3", "/home/wirepas/local_history_service/local_history_service.py"]

LABEL com.wirepas.gateway.build.sha1="${GATEWAY_BUILD_SHA1}"
