#!/usr/bin/env bash

set -e

rm -r dist || true

python3 -m build .

if ! command -v dpkg &>/dev/null; then
  echo "dpkg could not be found!"
  exit 1
fi

# In RaspberryPI, pip does not support the wheel file name suffix of linux_aarch64.whl which comes from OS architecture query to the OS itself of Python setuptools.
# Supported pip wheel file suffixes (pip compatible tags) listed using "pip debug --verbose" which doesn't include linux_aarch64 in RaspberryPI,
# and pip complains as the wheel file is not supported in this platform.
# Therefore, "linux_aarch64" file name suffix is changed with widely supported "py3-none-any" if dpkg architecture is "musl-linux-armhf"(possibly RaspberryPI).
muslv=$(dpkg --print-architecture)
if [ "$muslv" = "musl-linux-armhf" ]; then
  package_name=$(ls dist/*.tar.gz)
  new_whl_file=$(basename "$package_name" .tar.gz)-py3-none-any.whl
  old_whl_file=$(ls dist/*.whl)
  mv "$old_whl_file" "dist/${new_whl_file}"
  echo "WARNING: wirepas_gateway wheel file name changed for <pip> due to ARMHF OS architecture(possibly RaspberryPI) : dist/$new_whl_file"
fi
