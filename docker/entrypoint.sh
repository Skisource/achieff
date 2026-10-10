#!/bin/sh
set -eu

data_dir="${ACHIEFF_DATA_DIR:-/data}"
mkdir -p "$data_dir"
chown app:app "$data_dir"

exec setpriv --reuid=app --regid=app --init-groups --inh-caps=-all "$@"
