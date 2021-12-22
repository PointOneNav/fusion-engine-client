# TCP client application currently supported for Linux only.
if (UNIX)
    add_executable(tcp_client linux_tcp_client.cc)
    target_link_libraries(tcp_client PUBLIC fusion_engine_client)
    target_link_libraries(tcp_client PUBLIC print_message)
endif()
