add_subdirectory(common)

add_subdirectory(generate_data)
add_subdirectory(message_decode)
add_subdirectory(lband_decode)
add_subdirectory(tcp_client)
add_subdirectory(udp_client)

# Note that we do _not_ include the external_cmake_project/ subdirectory here.
# That application is designed as a standalone project, not built by the
# fusion-engine-client CMake project. See external_cmake_project/CMakeLists.txt
# for details.
