/**************************************************************************/ /**
 * @brief Emscripten bindings for structs in configuration.h.
 ******************************************************************************/

#include <emscripten/bind.h>
#include <emscripten/emscripten.h>

#include <point_one/fusion_engine/messages/core.h>

#include "binding_utils.h"

using namespace emscripten;
using namespace point_one::fusion_engine::messages;

/******************************************************************************/
EMSCRIPTEN_BINDINGS(control) {
    static auto CommandResponseMessage_MESSAGE_TYPE = CommandResponseMessage::MESSAGE_TYPE;
    static auto CommandResponseMessage_MESSAGE_VERSION = CommandResponseMessage::MESSAGE_VERSION;
    class_<CommandResponseMessage>("CommandResponseMessage")
        .constructor<>()
        .class_property("MESSAGE_TYPE", &CommandResponseMessage_MESSAGE_TYPE)
        .class_property("MESSAGE_VERSION", &CommandResponseMessage_MESSAGE_VERSION)
        .property("source_seq_number", &CommandResponseMessage::source_seq_number)
        .property("response", &CommandResponseMessage::response)
        .ARRAY_PROPERTY(CommandResponseMessage, reserved)
        .STRUCT_FUNCTIONS(CommandResponseMessage);

    static auto VersionInfoMessage_MESSAGE_TYPE = VersionInfoMessage::MESSAGE_TYPE;
    static auto VersionInfoMessage_MESSAGE_VERSION = VersionInfoMessage::MESSAGE_VERSION;
    class_<VersionInfoMessage>("VersionInfoMessage")
        .constructor<>()
        .class_property("MESSAGE_TYPE", &VersionInfoMessage_MESSAGE_TYPE)
        .class_property("MESSAGE_VERSION", &VersionInfoMessage_MESSAGE_VERSION)
        .property("system_time_ns", &VersionInfoMessage::system_time_ns)
        .property("fw_version_length", &VersionInfoMessage::fw_version_length)
        .property("engine_version_length", &VersionInfoMessage::engine_version_length)
        .property("hw_version_length", &VersionInfoMessage::hw_version_length)
        .property("rx_version_length", &VersionInfoMessage::rx_version_length)
        .ARRAY_PROPERTY(VersionInfoMessage, reserved)
        .ARRAY_PROPERTY(VersionInfoMessage, fw_version_str)
        .STRUCT_FUNCTIONS(VersionInfoMessage);

    static auto MessageRequest_MESSAGE_TYPE = MessageRequest::MESSAGE_TYPE;
    static auto MessageRequest_MESSAGE_VERSION = MessageRequest::MESSAGE_VERSION;
    class_<MessageRequest>("MessageRequest")
        .constructor<>()
        .class_property("MESSAGE_TYPE", &MessageRequest_MESSAGE_TYPE)
        .class_property("MESSAGE_VERSION", &MessageRequest_MESSAGE_VERSION)
        .property("message_type", &MessageRequest::message_type)
        .ARRAY_PROPERTY(MessageRequest, reserved)
        .STRUCT_FUNCTIONS(MessageRequest);
}
