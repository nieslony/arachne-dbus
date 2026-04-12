#!/bin/bash

ROOT="$(realpath $(dirname $0) )/../root"
PYTHON_VERSION=$( python --version | awk '{ gsub("\\.[0-9]+$", "", $2); print $2; }' )
RUN_DIR=/tmp/openvpn-server

mkdir -vp $RUN_DIR

PYTHONPATH=$ROOT/usr/local/lib/python$PYTHON_VERSION/site-packages/ \
    $ROOT/usr/local/bin/arachne-dbus --bus session --console-log --directory $RUN_DIR
