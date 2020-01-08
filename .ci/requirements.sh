#!/usr/bin/env bash
# Copyright 2019 Wirepas Ltd

sudo apt-get install build-essential libsystemd-dev dbus qemu-user-static libsystemd-dev
sudo gem install github_changelog_generator
pip3 install --upgrade twine
pip3 install pipenv
sudo ./.ci/install-repo.sh
./.ci/install-devtools.sh
pip3 install -r dev-requirements.txt
pip3 install -r python_transport/docs/requirements.txt
