# UDP client application currently supported for Linux only.
if (UNIX)
    add_executable(udp_client linux_udp_client.cc)
    target_link_libraries(udp_client PUBLIC fusion_engine_client)
    target_link_libraries(udp_client PUBLIC print_message)
endif()
