# Duplicate of transport service for now
ARG BASE_IMAGE=python:3.13-alpine3.21
FROM $BASE_IMAGE AS builder

RUN adduser --disabled-password wirepas

RUN apk add --no-cache \
		build-base \
		# Needed for the wheel generation:
		bash \
		dpkg \
		# Needed for dbus_c.c:
		elogind-dev \
		# Needed for PyGObject:
		cairo-dev \
		gobject-introspection-dev

RUN python3 -m pip install build

USER wirepas
WORKDIR /home/wirepas

COPY --chown=wirepas ./python_transport /home/wirepas/python_transport
WORKDIR /home/wirepas/python_transport

RUN ./utils/generate_wheel.sh

USER wirepas

# Needed by pydbus
RUN pip3 install PyGObject~=3.0 --user

# Install protobuf from source to get the UPB implementation
RUN pip3 install dist/wirepas_gateway*.whl --no-binary protobuf --user


# Build the final image
FROM $BASE_IMAGE AS runner

RUN adduser --disabled-password wirepas

# Variable set from CI
ARG GATEWAY_BUILD_SHA1=unset

RUN apk add --no-cache libelogind glib gobject-introspection

USER wirepas

ENV PATH="/home/wirepas/.local/bin:${PATH}"

# Copy the built wheel and its dependencies from builder
COPY --from=builder /home/wirepas/.local /home/wirepas/.local

# Sanity check to confirm we have the UPB implementation for protobuf
RUN python3 -c "import sys;\
from google.protobuf.internal import api_implementation;\
sys.exit(0 if api_implementation.Type() == 'upb' else 1)"

COPY ./local_history_service/*.py /home/wirepas/local_history_service/

CMD ["python3", "/home/wirepas/local_history_service/local_history_service.py"]

LABEL com.wirepas.gateway.build.sha1="${GATEWAY_BUILD_SHA1}"
