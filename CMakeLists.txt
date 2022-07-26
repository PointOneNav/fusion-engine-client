# Copyright (C) Point One Navigation - All Rights Reserved
cmake_minimum_required(VERSION 3.3.2)

# Set toolchain parameters before calling project().
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Define the project and setup the compiler toolchain.
project(p1_fusion_engine_client)

# Option definitions.
option(BUILD_SHARED_LIBS "Build shared libraries instead of static libraries."
       ON)

option(BUILD_EXAMPLES "Build example applications." ON)

# Set additional compilation flags.
if (MSVC)
    add_compile_options(/W4 /WX)
else()
    add_compile_options(-Wall -Werror)
endif()

################################################################################
# Library Definitions
################################################################################

# Define the fusion_engine_client library and supporting code.
add_library(fusion_engine_client
            src/point_one/fusion_engine/common/logging.cc
            src/point_one/fusion_engine/messages/crc.cc
            src/point_one/fusion_engine/parsers/fusion_engine_framer.cc)
target_include_directories(fusion_engine_client PUBLIC ${PROJECT_SOURCE_DIR}/src)
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
