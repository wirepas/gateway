#!/usr/bin/env bash
# Wirepas Oy

source ./modules/git.sh

WM_USER=${1:-"false"}

if [ ! ${WM_USER} == "false" ]
then

   git_clone_repo "c-mesh-api" "sink_service/c-mesh-api"
   git_clone_repo "public-apis" "public-apis"

else

   echo "please provice firstname.lastname as arguments"

fi
