#!/usr/bin/env bash

set -e

red='\033[31m'
white='\033[97m'


if [ ! -f "Cargo.toml" ]; then
  >2& echo "${red}Please run this script from the project root.${white}" && exit 1
fi

docker build -t rust-python .

wheel_command=$(cat ./scripts/create_wheel.sh)

py3.7() { docker run --mount type=bind,source=$PWD,target=$PWD -w=$PWD rust-python bash -c "$@"; }

py3.7 "$wheel_command"
