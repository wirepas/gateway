#!/usr/bin/env bash
# Wirepas Oy

source ./modules/git.sh

git_clone_repo "c-mesh-api" "sink_service/c-mesh-api"
git_clone_repo "backend-apis" "public-apis"
