FROM python:3.7.7-buster AS builder

RUN useradd -ms /bin/bash wirepas
RUN apt-get update

RUN apt-get install -y \
	python3-dev \
        python3-gi \
        libsystemd-dev \
        libgirepository1.0-dev 

USER wirepas

COPY --chown=wirepas ./python_transport /home/wirepas/python_transport

WORKDIR /home/wirepas/python_transport

RUN python3 -m pip install --no-cache-dir --upgrade pip \
    && python3 -m pip install wheel setuptools \
    && ./utils/generate_wheel.sh

RUN pip3 install PyGObject --user
RUN pip3 install dist/wirepas_gateway*.whl --user


FROM python:3.7.7-slim-buster

RUN useradd -ms /bin/bash wirepas

RUN apt-get update \
    && apt-get install -y python3-gi \
    && rm -fr /var/libapt/lists/*

# Copy the built wheel and its dependencies from builder
COPY --from=builder /home/wirepas/.local /home/wirepas/.local

USER wirepas

ENV PATH="/home/wirepas/.local/bin:${PATH}"

CMD ["wm-gw"]
