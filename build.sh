#!/usr/bin/env bash

lightgreen='\033[92m'
red='\033[31m'
cyan='\033[36m'
white='\033[97m'

filename-only() {
    local without_extension=${1%.*}
    echo "${without_extension##*/}" # strips path
}

usage() {
  # less either acts as `cat` or actually page the output, depending on TTY and terminal window size.
  less -XF <<EOF
  DESCRIPTION
    Builds a dockerfile capable of running the bot.


  EXAMPLES
    # tag the build as jjorissen/epic-reminder and push the result
    $(filename-only $0) -t jjorissen/epic-reminder -p

  USAGE
    $(filename-only $0) [-p] [-t TAG]


  FLAGS
    -t TAG   Tag the resulting image with the provided tag,
             can be used multiple times. Note that the build
             is tagged with epic-reminder if no tag is provided.

    -p       Push the resulting image (docker push TAG --all-tags).
             Cannot push without at least one provided tag.

    -s       Skip testing after the build

    -q       No output, does not ask for user input

    -h       Show help
EOF
}

push=""
skip_tests=""
quiet=""
tags=""
while getopts ":t:psq" o; do
    case "${o}" in
        t)
            if [ -z "${tags}" ]; then
              first_tag="${OPTARG}"
            fi
            tags="${tags} ${OPTARG}";;
        p)
            push=1;;
        s)
            skip_tests=1;;
        q)
            quiet=1;;
        *)
            usage $0
            exit 1
            ;;
    esac
done
shift $((OPTIND-1))

{
  echo /venv
  echo ".*"
  echo build.sh
  echo Dockerfile

  # the below section calculates whether files should be ignored based on our .gitignore config
  git check-ignore ./*
  # check anything except the crafting symlink
  git check-ignore $(find ./epic* -type file)
  # check based on ignored directories
  git check-ignore $(find ./epic* -type dir)
  git check-ignore ./materials/*
  git check-ignore ./materials/.*
  git check-ignore $(find ./materials/* -maxdepth 2 -type dir)
} > .dockerignore

if [ -z "${first_tag}" ]; then
  first_tag="epic-reminder"
  nopush="1"
fi

set -e
# shellcheck disable=SC2046
docker build $(for tag in ${tags}; do echo -t "${tag}"; done) .
if [ -z "$quiet" ]; then
  docker run -it ${first_tag} tree -a

  >&2 echo -e "${red}Verify that the tree above does not show any files that should be excluded before pushing.${white}"

  if [ -n "${push}" ] || [ -z "${skip_tests}" ]; then
    >&2 echo -e "${lightgreen}Press [Enter] to proceed or Ctrl+C to stop>${white}"
    # shellcheck disable=SC2034
    # shellcheck disable=SC2162
  read i
  fi
fi

if [ -z "${skip_tests}" ]; then
  docker run -w=/app/materials ${first_tag} python -m unittest discover -p "*test.py"
fi

if [ -n "${push}" ]; then
  if [ -n "${nopush}" ]; then
    >&2 echo -e "${red}Cannot push with no provided tag.${white}" || exit 1
  fi
  set +e
  error="$(docker push ${first_tag} --all-tags 2>&1)"
  if [ $? -ne 0 ]; then
    >&2 echo -e "${red}encountered error=${error}; pushing with ${first_tag} only.${white}"
    docker push ${first_tag}
  fi
fi
