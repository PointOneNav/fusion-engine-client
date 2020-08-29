# Copyright (C) Point One Navigation - All Rights Reserved
project(p1_fusion_engine_client)

cmake_minimum_required(VERSION 3.0.2)

# Option definitions.
option(BUILD_SHARED_LIBS "Build shared libraries instead of static libraries."
       ON)

option(BUILD_EXAMPLES "Build example applications." ON)

# Set compilation flags.
set(CMAKE_CXX_FLAGS "-Wall -Werror")
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED True)

################################################################################
# Library Definitions
################################################################################

# Add the source directory to the include path.
include_directories(${PROJECT_SOURCE_DIR}/src)

# All messages and supporting code.
add_library(fusion_engine_client
            src/point_one/messages/crc.cc)

# Install targets.
install(TARGETS fusion_engine_client)

install(DIRECTORY src/point_one DESTINATION include
        FILES_MATCHING PATTERN "*.h")

################################################################################
# Example Applications
################################################################################

if (BUILD_EXAMPLES)
    add_subdirectory(examples)
endif()
