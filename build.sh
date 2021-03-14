#!/usr/bin/env bash

set -e

lightgreen='\033[92m'
red='\033[31m'
cyan='\033[36m'
white='\033[97m'

{
  echo /venv
  echo ".*"
  # calculate whether files should be ignored based on our .gitignore config
  git check-ignore ./*
  git check-ignore ./epic/**/*
  git check-ignore ./epic_reminder/*
  git check-ignore ./epic_reminder/**/*
  git check-ignore ./materials/*
} > .dockerignore

docker build -t epic-reminder .
docker run -it epic-reminder tree -a

>&2 echo -e "${red}Verify that the tree above does not show any files that should be excluded before pushing.${white}"
>&2 echo -e "${lightgreen}Result tagged as ${cyan}epic-reminder${lightgreen}.${white}"
>&2 echo -e "${lightgreen}Press [Enter] to run tests>${white}"
# shellcheck disable=SC2034
# shellcheck disable=SC2162
read i
docker run -w=/app/materials epic-reminder python setup.py test
