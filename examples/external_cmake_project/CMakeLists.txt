################################################################################
# This is a simple example of how to import the fusion-engine-client library in
# your own project using the CMake FetchContent feature. We strongly encourage
# you to use FetchContent to download fusion-engine-client from the publicly
# available source code.
#
# Alternatively, you may choose to use a git submodule to import the source code
# into your repository. We do not recommend copying the fusion-engine-client
# source code directly into your repository. Doing so makes it much more
# difficult to receive updates as new features and improvements are released.
################################################################################

cmake_minimum_required(VERSION 3.12)

set(CMAKE_CXX_STANDARD 14)

project(fusion_engine_usage_example C CXX)

# Use FetchContent to import the fusion-engine-client C++ library using Git.
#
# Note that we always recommend using a specific version of the library in your
# code by specifying a release zip file or a git tag (e.g., `GIT_TAG vA.B.C`),
# and updating that as new versions are released. That way, you can be sure that
# your code is always built with a known version of fusion-engine-client. If you
# prefer, however, you can set the GIT_TAG to track the latest changes by
# setting `GIT_TAG master` below.
#
# We explicitly disable example applications from the fusion-engine-client
# library by setting P1_FE_BUILD_EXAMPLES to OFF below. We only want to build
# the library and make the fusion_engine_client CMake target available here. By
# default, if we do not tell it otherwise, FetchContent_MakeAvailable() will
# also import all of the example applications in fusion-engine-client/examples/.
#
# It is important to specify it as an INTERNAL variable. If you do not do this,
# the option definition in the fusion-engine-client CMakeLists.txt file will
# override this value and enable the example applications anyway. This is a
# result of CMP0077, which was added in CMake 3.13.
include(FetchContent)
FetchContent_Declare(
    fusion_engine_client
    # Recommended:
    URL https://github.com/PointOneNav/fusion-engine-client/archive/refs/tags/v1.22.3.zip
    URL_HASH MD5=cfe1de319725822a1b825cd3421fb6b1
    # Or alternatively:
    # GIT_REPOSITORY https://github.com/PointOneNav/fusion-engine-client.git
    # GIT_TAG v1.22.3
)
set(P1_FE_BUILD_EXAMPLES OFF CACHE INTERNAL "")
FetchContent_MakeAvailable(fusion_engine_client)

# Now we define an example application that uses the fusion-engine-client
# library. In your own code, you can link any add_executable() or add_library()
# target with fusion-engine-client by calling target_link_libraries() as shown.
add_executable(example_app main.cc)
target_link_libraries(example_app PUBLIC fusion_engine_client)
