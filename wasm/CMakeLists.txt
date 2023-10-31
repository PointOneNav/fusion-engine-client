# Copyright (C) Point One Navigation - All Rights Reserved
cmake_minimum_required(VERSION 3.14)

# Set toolchain parameters before calling project().
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# WASM libraries must be linked statically.
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)

# Define the project and setup the compiler toolchain.
project(p1_fe_wasm)

# Import FusionEngine client.
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/..
                 ${CMAKE_CURRENT_BINARY_DIR}/fusion_engine_client
                 EXCLUDE_FROM_ALL)

# Define the WASM binding library.
add_executable(fusion_engine_client_wasm
               command_control_bindings.cc
               configuration_bindings.cc
               defs_binding.cc
               device_binding.cc
               fusion_engine_framer_binding.cc
               fault_bindings.cc
               gnss_corrections_bindings.cc
               measurements_binding.cc
               ros_bindings.cc
               solution_binding.cc
               signal_defs_bindings.cc)
target_include_directories(fusion_engine_client_wasm PUBLIC
                           ${CMAKE_CURRENT_SOURCE_DIR}})
target_link_libraries(fusion_engine_client_wasm PUBLIC fusion_engine_client)
set(CMAKE_EXECUTABLE_SUFFIX ".js")
set_target_properties(fusion_engine_client_wasm PROPERTIES
    LINK_FLAGS
    "-s WASM=1 -s NO_EXIT_RUNTIME=1 -sMODULARIZE -s EXPORT_ES6=1 -lembind")
