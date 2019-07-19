#!/usr/bin/env bash

set -e

# shellcheck disable=SC1091
source container/common/generate_settings.sh

generate_settings container/common/wm_transport_service.template container/common/wm_transport_service.yml
