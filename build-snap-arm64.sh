#!/usr/bin/env bash
# export SNAPCRAFT_BUILD_ENVIRONMENT=lxd
sudo snapcraft clean 
sudo snapcraft --target-arch=arm64 --enable-experimental-target-arch 
