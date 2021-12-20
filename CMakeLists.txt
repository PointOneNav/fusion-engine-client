# Copyright (C) Point One Navigation - All Rights Reserved
project(p1_fusion_engine_client)

cmake_minimum_required(VERSION 3.3.2)

# Option definitions.
option(BUILD_SHARED_LIBS "Build shared libraries instead of static libraries."
       ON)

option(BUILD_EXAMPLES "Build example applications." ON)

# Set compilation flags.
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED True)

if (MSVC)
    add_compile_options(/W4 /WX)
else()
    add_compile_options(-Wall -Werror)
endif()

################################################################################
# Library Definitions
################################################################################

# Add the source directory to the include path.
include_directories(${PROJECT_SOURCE_DIR}/src)

# All messages and supporting code.
add_library(fusion_engine_client
            src/point_one/fusion_engine/common/logging.cc
            src/point_one/fusion_engine/messages/crc.cc)
if (MSVC)
    target_compile_definitions(fusion_engine_client PRIVATE BUILDING_DLL)
endif()

# Install targets.
install(TARGETS fusion_engine_client
        LIBRARY DESTINATION lib)

install(DIRECTORY src/point_one DESTINATION include
        FILES_MATCHING PATTERN "*.h")

################################################################################
# Example Applications
################################################################################

if (BUILD_EXAMPLES)
    add_subdirectory(examples)
endif()
