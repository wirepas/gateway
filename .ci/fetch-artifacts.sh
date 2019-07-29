#!/usr/bin/env bash
# Copyright 2019 Wirepas Ltd

BUILD_TAG=${TRAVIS_TAG:-"edge"}

rm -rf dist/ || true
mkdir dist

USERGROUP="$(id -u):$(id -g)"
COMMAND="cp -v --no-preserve=ownership \${TRANSPORT_SERVICE}/wirepas_gateway-* . \
         && cp -v --no-preserve=ownership /usr/local/bin/sinkService . \
         && tar -czvf sinkService-\${ARCH}.tar.gz sinkService \
         && rm sinkService \
         && chown -R ${USERGROUP} /data"

echo "fetching x86 wheel"
docker run \
        --rm \
        --user root \
        -it \
        -e ARCH="x86" \
        -w /data \
        -v "$(pwd)/dist":/data \
        wirepas/gateway-x86:"${BUILD_TAG}" \
        bash -c "${COMMAND}"

echo "fetching arm wheel"
docker run \
        --rm \
        --user root \
        -e ARCH="arm" \
        -w /data \
        -v /usr/bin/qemu-arm-static:/usr/bin/qemu-arm-static \
        -v "$(pwd)/dist":/data \
        wirepas/gateway-arm:"${BUILD_TAG}" \
        bash -c "${COMMAND}"

twine check dist/wirepas_gateway*
