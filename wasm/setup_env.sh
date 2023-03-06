#!/bin/bash

set -e

    ################################################################################
#Set Directory Locations
    ################################################################################

#Find the directory of this file, following symlinks.
#
#Reference:
#- https: //stackoverflow.com/questions/59895/how-to-get-the-source-directory-of-a-bash-script-from-within-the-script-itself
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

################################################################################
# Run
################################################################################

# If emsdk is not available, try to activate it.
if [[ -z "${EMSDK}" ]]; then
    if [[ -z "${EMSDK_DIR}" ]]; then
        EMSDK_DIR="${SCRIPT_DIR}/emsdk"
    fi

    # If emsdk doesn't exist, download it.
    if [[ ! -f "${EMSDK_DIR}/emsdk_env.sh" ]]; then
      echo "Emscripten SDK not found. Downloading..."
      git clone https://github.com/emscripten-core/emsdk.git "${EMSDK_DIR}"
      pushd "${EMSDK_DIR}" >/dev/null
      ./emsdk install latest
      ./emsdk activate latest
      popd >/dev/null
    fi

    # Activate emsdk.
    echo "Activating Emscripten SDK from ${EMSDK_DIR}..."
    source "${EMSDK_DIR}/emsdk_env.sh"
fi

echo "Emscripten SDK ${EMSDK} activated."
