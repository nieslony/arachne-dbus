#!/bin/bash

ROOT=../root

PYTHONPATH=$ROOT/usr/local/lib/python3.13/site-packages/ \
    $ROOT/usr/local/bin/arachne-dbus --bus session --console-log --directory /tmp
