#!/bin/bash

set -e

################################################################################
# Set Directory Locations
################################################################################

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
BUILD_DIR="${SCRIPT_DIR}/build"

################################################################################
# Parse Arguments
################################################################################

CMAKE_ARGS=

MAKE_TARGETS=()

function usage() {
    cat <<EOF
Usage: $0 [OPTION]...

Compile this project.

OPTIONS
   -h, --help
       Display this usage information.
   -t, --target NAME
       Compile the specified target name. May be specified multiple times. By
       default, all available targets will be built.

Any command-line arguments beginning with -D will be passed to cmake:
  > $0 -DCMAKE_BUILD_TOOLCHAIN=/path/to/file
  Becomes:
  > cmake -DCMAKE_BUILD_TOOLCHAIN=/path/to/file

All other arguments will be passed to make:
  > $0 -j4
  Becomes:
  > make -j4
EOF
}

options=$(getopt -o D:ht: -l help,target: -- "$@")
eval set -- "$options"

while true ; do
    case "$1" in
    -D)
        shift
        CMAKE_ARGS="${CMAKE_ARGS} $1"
        ;;
    -h|--help)
        usage
        exit 0
        ;;
    -t|--target)
        shift
        MAKE_TARGETS+=("$1")
        ;;
    --)
        shift
        break
        ;;
    *)
        break
        ;;
    esac
    shift
done

MAKE_ARGS=$*

################################################################################
# Run
################################################################################

# Set default targets list.
if [ ${#MAKE_TARGETS[@]} -eq 0 ]; then
    MAKE_TARGETS=("fusion_engine_client_wasm")
fi

# Setup emsdk if needed.
source "${SCRIPT_DIR}/setup_env.sh"

# Build the library.
#
# Specify arguments to make on the command line for this script. For example:
#   ./build.sh -j  # Parallel build
#   ./build.sh VERBOSE=T  # Verbose build
mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"
emcmake cmake ${CMAKE_ARGS} ${SCRIPT_DIR}
emmake make ${MAKE_ARGS} "${MAKE_TARGETS[@]}"

for MAKE_TARGET in "${MAKE_TARGETS[@]}"; do
    emcc -o ${MAKE_TARGET}.js \
         -Wl,--whole-archive lib${MAKE_TARGET}.a -Wl,--no-whole-archive \
         -O2 \
         -s NO_EXIT_RUNTIME=1 \
         -sMODULARIZE -s EXPORT_ES6=1 \
         -lembind
done
