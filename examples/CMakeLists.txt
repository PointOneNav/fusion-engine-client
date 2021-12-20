add_subdirectory(generate_data)
add_subdirectory(message_decode)

# TCP client application currently Linux only.
if (UNIX)
    add_subdirectory(tcp_client)
endif()
