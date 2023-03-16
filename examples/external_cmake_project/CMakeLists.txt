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

# We explicitly set the CMake CMP0077 policy to NEW before calling FetchContent
# below. This policy was adding in CMake 3.12. Setting it to NEW makes it so
# set() calls here are not overridden by option() definitions in the external
# library. With default value (OLD), the option() value will be used.

# Specifically, here we want to set(P1_FE_BUILD_EXAMPLES OFF). If we do not set
# CMP0077 to NEW, the option(P1_FE_BUILD_EXAMPLES ON) definition inside the
# fusion-engine-client CMake file will ignore that value and set it to ON.
set(CMAKE_POLICY_DEFAULT_CMP0077 NEW)

set(CMAKE_CXX_STANDARD 14)

# Disable example applications from the fusion-engine-client library imported
# below. We want to build the library and make the fusion_engine_client CMake
# target available here. If we do not do this, teh add_subdirectory() call below
# will also import all of the example applications in
# fusion-engine-client/examples/.
set(P1_FE_BUILD_EXAMPLES OFF)

project(fusion_engine_usage_example C CXX)

# Use FetchContent to import the fusion-engine-client C++ library using Git.
#
# Note that we always recommend using a specific version of the library in your
# code by specifying a git tag (e.g., `GIT_TAG v1.15.2`), and updating that as
# new versions are released. That way, you can be sure that your code is always
# built with a known version of fusion-engine-client.
#
# If you prefer, however, you can set the GIT_TAG to track the latest changes by
# setting `GIT_TAG master` below.
include(FetchContent)
FetchContent_Declare(
    fusion_engine_client
    GIT_REPOSITORY https://github.com/PointOneNav/fusion-engine-client.git
    GIT_TAG v1.16.0
)
FetchContent_Populate(fusion_engine_client)
add_subdirectory(${fusion_engine_client_SOURCE_DIR})

# Now we define an example application that uses the fusion-engine-client
# library. In your own code, you can link any add_executable() or add_library()
# target with fusion-engine-client by calling target_link_libraries() as shown.
add_executable(example_app main.cc)
target_link_libraries(example_app PUBLIC fusion_engine_client)
