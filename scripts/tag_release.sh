#!/bin/bash

# Find the directory of this file, following symlinks.
#
# Reference:
# - https://stackoverflow.com/questions/59895/how-to-get-the-source-directory-of-a-bash-script-from-within-the-script-itself
get_parent_dir() {
    local SOURCE="${BASH_SOURCE[0]}"
    while [ -h "$SOURCE" ]; do
        local DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
        SOURCE="$(readlink "$SOURCE")"
        [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
    done

    local PARENT_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
    echo "${PARENT_DIR}"
}

SCRIPT_DIR=$(get_parent_dir)

REPO_ROOT=$(git rev-parse --show-toplevel)

# Print help details.
show_usage() {
    cat <<EOF
Usage: $0 [OPTIONS...] VERSION [COMMIT]

Tag a new release with the specified VERSION string, and update the version
details in the code.

VERSION must follow the Python version format outlined in PEP 440:
    [N!]N(.N)*[{a|b|rc}N][.postN][.devN]

For example, 1.15.3 or 1.16.2rc4.dev3.

If COMMIT is not specified, tag the current commit.


OPTIONS:

    -h, --help
        Show this help message.
    -f, --force
        Tag the release even if VERSION is equal to or older than the most
        recent release. If a tag already exists for VERSION, delete it.
EOF
}

################################################################################
# Handle Arguments
################################################################################

FORCE=

parse_args() {
    # Process command line arguments.
    args=()
    while [ "$1" != "" ]; do
    case $1 in
        -h | --help)
            show_usage
            exit 0
            ;;
        -f | --force)
            FORCE=T
            ;;
        --)
            shift
            args+=($*)
            break
            ;;
        *)
            if [[ "$1" == -* ]]; then
              args+=($1)
            else
              args+=("$1")
            fi
            ;;
    esac
    shift
    done
}

parse_args "$@"
set -- "${args[@]}"

VERSION=$1
if [[ -z "${VERSION}" ]]; then
  printf "Error: Version not specified.\n\n"
  show_usage
  exit 1
fi

COMMIT=$2
if [[ -z "${COMMIT}" ]]; then
  COMMIT="HEAD"
fi

TAG="v${VERSION}"

################################################################################
# Run Application
################################################################################

pushd ${REPO_ROOT} >/dev/null

# Check if the specified version is already tagged.
echo "Checking requested version (${VERSION})."
if git describe --tags --abbrev=0 --match ${TAG} >/dev/null 2>/dev/null; then
  if [[ -n "${FORCE}" ]]; then
    echo "A tag with the specified version already exists. Deleting and overwriting."
    git tag -d ${TAG}
  else
    echo "Error: A tag with the specified version already exists. Use --force to overwrite."
    exit 2
  fi
fi

# If this is a release candidate or dev tag, check if there is an N-1 tag
# (1.20.3rc2 for TAG=1.20.3rc3). If so, we'll use its tag message as an initial
# template for this one.
if [[ "${TAG}" =~ (.*(rc|dev))([0-9]+)$ ]]; then
  PREV_TAG="${BASH_REMATCH[1]}$((${BASH_REMATCH[3]} - 1))";
  if git describe --tags --abbrev=0 --match ${PREV_TAG} >/dev/null 2>/dev/null; then
    echo "Found previous tag ${PREV_TAG}. Using it as a template for ${TAG}."
  else
    PREV_TAG=""
  fi
fi

# Checkout the requested commit.
if [[ "${COMMIT}" != "HEAD" ]]; then
  echo "Checking out requested commit."
  git checkout ${COMMIT} 2>/dev/null
fi

COMMIT=$(git rev-parse HEAD)
COMMIT_MESSAGE=$(git log --format=%s -n1 HEAD)
echo "Using commit ${COMMIT} (${COMMIT_MESSAGE})."

# Get the most recently released version _before_ the requested commit. If the
# requested commit is older than the latest release on current master, this
# will not be the latest release version. This is useful if you need to create
# a patch to a previous release, but current master is on a newer major/minor
# version. For example, if the latest release is 1.15.0, you might still want
# to release version 1.14.1 to patch a bug in 1.14.0.
PREV_VERSION=$(git describe --tags --abbrev=0 --match "v*" | sed -e 's/^v//')
PREV_COMMIT=$(git rev-parse v${PREV_VERSION})
echo "Found previous version ${PREV_VERSION} (commit ${PREV_COMMIT})."

# Check if the new version is older than the current version.
cat <<EOF | python3
from packaging import version
import sys

prev_version = version.parse("${PREV_VERSION}")
new_version = version.parse("${VERSION}")

if new_version <= prev_version:
    sys.exit(1)
EOF
if [[ $? -ne 0 ]]; then
  if [[ -n "${FORCE}" ]]; then
    echo "Warning: The specified version is not newer than the current version. Tagging anyway."
  else
    echo "Error: The specified version is not newer than the current version. Use --force to override."
    exit 3
  fi
fi

# Update the version string in the C++ library.
echo "Updating C++ library version string."
CPP_VERSION_PATH="src/point_one/fusion_engine/common/version.h"
cat <<EOF | python3
from packaging import version

new_version = version.parse("${VERSION}")

with open('${CPP_VERSION_PATH}', 'wt') as f:
    f.write(f'''\
/**************************************************************************/ /**
 * @brief Library version macros.
 ******************************************************************************/

#pragma once

#define P1_FUSION_ENGINE_VERSION_STRING "{str(new_version)}"
#define P1_FUSION_ENGINE_VERSION_MAJOR {new_version.major}
#define P1_FUSION_ENGINE_VERSION_MINOR {new_version.minor}
#define P1_FUSION_ENGINE_VERSION_PATCH {new_version.micro}
''')
EOF
git add "${CPP_VERSION_PATH}"

# Update the version string in the C++ CMake file.
#
# Note: CMake does not support version suffixes like rc3, etc., so we only use
# the major.minor.patch version here.
echo "Updating CMake project version string."
CMAKE_PATH="CMakeLists.txt"
cat <<EOF | python3
import re
from packaging import version

new_version = version.parse("${VERSION}")

with open('${CMAKE_PATH}', 'rt') as f:
    cmake_contents = f.read()

with open('${CMAKE_PATH}', 'wt') as f:
    f.write(re.sub(
        r'project\\((.* VERSION) .*\\)',
        f'project(\\\\1 {new_version.major}.{new_version.minor}.{new_version.micro})',
        cmake_contents))
EOF
git add "${CMAKE_PATH}"

# Update the version string in the Python library.
echo "Updating Python library version string."
PYTHON_INIT_PATH="python/fusion_engine_client/__init__.py"
sed -i -e "s/__version__ = '.*'/__version__ = '${VERSION}'/" "${PYTHON_INIT_PATH}"
git add "${PYTHON_INIT_PATH}"

# Now commit the changes.
if ! git diff -s --exit-code --cached; then
  echo "Committing changes."
  git commit -m "Updated the library version number to ${VERSION}." >/dev/null
  COMMIT=$(git rev-parse HEAD)
fi

# Tag the updated git commit.
echo "Tagging commit ${COMMIT} as '${TAG}'."
if [[ -z "${PREV_TAG}" ]]; then
  cat <<EOF | git tag -a ${TAG} ${COMMIT} --edit -F -
Release version ${VERSION}.

New Features

Changes

Fixes
EOF
else
  git tag -l --format='%(contents)' ${PREV_TAG} | \
      perl -pe 'chomp if eof' | \
      git tag -a ${TAG} ${COMMIT} --edit -F -
fi
