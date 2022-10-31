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
EMSCRIPTEN_BINDINGS(configuration) {
    enum_<ConfigType>("ConfigType")
        .value("INVALID", ConfigType::INVALID)
        .value("DEVICE_LEVER_ARM", ConfigType::DEVICE_LEVER_ARM)
        .value("DEVICE_COARSE_ORIENTATION", ConfigType::DEVICE_COARSE_ORIENTATION)
        .value("GNSS_LEVER_ARM", ConfigType::GNSS_LEVER_ARM)
        .value("OUTPUT_LEVER_ARM", ConfigType::OUTPUT_LEVER_ARM)
        .value("VEHICLE_DETAILS", ConfigType::VEHICLE_DETAILS)
        .value("WHEEL_CONFIG", ConfigType::WHEEL_CONFIG)
        .value("HARDWARE_TICK_CONFIG", ConfigType::HARDWARE_TICK_CONFIG)
        .value("UART1_BAUD", ConfigType::UART1_BAUD)
        .value("UART2_BAUD", ConfigType::UART2_BAUD)
        .value("UART1_OUTPUT_DIAGNOSTICS_MESSAGES", ConfigType::UART1_OUTPUT_DIAGNOSTICS_MESSAGES)
        .value("UART2_OUTPUT_DIAGNOSTICS_MESSAGES", ConfigType::UART2_OUTPUT_DIAGNOSTICS_MESSAGES)
        .value("ENABLE_WATCHDOG_TIMER", ConfigType::ENABLE_WATCHDOG_TIMER);

    enum_<ConfigurationSource>("ConfigurationSource")
        .value("ACTIVE", ConfigurationSource::ACTIVE)
        .value("SAVED", ConfigurationSource::SAVED);

    enum_<SaveAction>("SaveAction")
        .value("SAVE", SaveAction::SAVE)
        .value("REVERT_TO_SAVED", SaveAction::REVERT_TO_SAVED)
        .value("REVERT_TO_DEFAULT", SaveAction::REVERT_TO_DEFAULT);

    static auto SetConfigMessage_MESSAGE_TYPE = SetConfigMessage::MESSAGE_TYPE;
    static auto SetConfigMessage_MESSAGE_VERSION = SetConfigMessage::MESSAGE_VERSION;
    static auto SetConfigMessage_FLAG_APPLY_AND_SAVE = SetConfigMessage::FLAG_APPLY_AND_SAVE;
    class_<SetConfigMessage>("SetConfigMessage")
        .constructor<>()
        .class_property("MESSAGE_TYPE", &SetConfigMessage_MESSAGE_TYPE)
        .class_property("MESSAGE_VERSION", &SetConfigMessage_MESSAGE_VERSION)
        .class_property("FLAG_APPLY_AND_SAVE", &SetConfigMessage_FLAG_APPLY_AND_SAVE)
        .property("config_type", &SetConfigMessage::config_type)
        .property("flags", &SetConfigMessage::flags)
        .ARRAY_PROPERTY(SetConfigMessage, reserved)
        .property("config_length_bytes", &SetConfigMessage::config_length_bytes)
        .STRUCT_FUNCTIONS(SetConfigMessage);

    static auto GetConfigMessage_MESSAGE_TYPE = GetConfigMessage::MESSAGE_TYPE;
    static auto GetConfigMessage_MESSAGE_VERSION = GetConfigMessage::MESSAGE_VERSION;
    class_<GetConfigMessage>("GetConfigMessage")
        .constructor<>()
        .class_property("MESSAGE_TYPE", &GetConfigMessage_MESSAGE_TYPE)
        .class_property("MESSAGE_VERSION", &GetConfigMessage_MESSAGE_VERSION)
        .property("config_type", &GetConfigMessage::config_type)
        .property("request_source", &GetConfigMessage::request_source)
        .ARRAY_PROPERTY(GetConfigMessage, reserved)
        .STRUCT_FUNCTIONS(GetConfigMessage);

    static auto SaveConfigMessage_MESSAGE_TYPE = SaveConfigMessage::MESSAGE_TYPE;
    static auto SaveConfigMessage_MESSAGE_VERSION = SaveConfigMessage::MESSAGE_VERSION;
    class_<SaveConfigMessage>("SaveConfigMessage")
        .constructor<>()
        .class_property("MESSAGE_TYPE", &SaveConfigMessage_MESSAGE_TYPE)
        .class_property("MESSAGE_VERSION", &SaveConfigMessage_MESSAGE_VERSION)
        .property("action", &SaveConfigMessage::action)
        .STRUCT_FUNCTIONS(SaveConfigMessage);

    static auto ConfigResponseMessage_MESSAGE_TYPE = ConfigResponseMessage::MESSAGE_TYPE;
    static auto ConfigResponseMessage_MESSAGE_VERSION = ConfigResponseMessage::MESSAGE_VERSION;
    class_<ConfigResponseMessage>("ConfigResponseMessage")
        .constructor<>()
        .class_property("MESSAGE_TYPE", &ConfigResponseMessage_MESSAGE_TYPE)
        .class_property("MESSAGE_VERSION", &ConfigResponseMessage_MESSAGE_VERSION)
        .property("config_source", &ConfigResponseMessage::config_source)
        .property("active_differs_from_saved", &ConfigResponseMessage::active_differs_from_saved)
        .property("config_type", &ConfigResponseMessage::config_type)
        .property("response", &ConfigResponseMessage::response)
        .ARRAY_PROPERTY(ConfigResponseMessage, reserved)
        .property("config_length_bytes", &ConfigResponseMessage::config_length_bytes)
        .STRUCT_FUNCTIONS(ConfigResponseMessage);

    class_<Point3f>("Point3f")
        .constructor<>()
        .property("x", &Point3f::x)
        .property("y", &Point3f::y)
        .property("z", &Point3f::z)
        .STRUCT_FUNCTIONS(Point3f);

    class_<CoarseOrientation>("CoarseOrientation")
        .constructor<>()
        .property("x_direction", &CoarseOrientation::x_direction)
        .property("z_direction", &CoarseOrientation::z_direction)
        .STRUCT_FUNCTIONS(CoarseOrientation);

    enum_<CoarseOrientation::Direction>("Direction")
        .value("FORWARD", CoarseOrientation::Direction::FORWARD)
        .value("BACKWARD", CoarseOrientation::Direction::BACKWARD)
        .value("LEFT", CoarseOrientation::Direction::LEFT)
        .value("RIGHT", CoarseOrientation::Direction::RIGHT)
        .value("UP", CoarseOrientation::Direction::UP)
        .value("DOWN", CoarseOrientation::Direction::DOWN)
        .value("INVALID", CoarseOrientation::Direction::INVALID);

    enum_<VehicleModel>("VehicleModel")
        .value("UNKNOWN_VEHICLE", VehicleModel::UNKNOWN_VEHICLE)
        .value("DATASPEED_CD4", VehicleModel::DATASPEED_CD4)
        .value("J1939", VehicleModel::J1939)
        .value("LEXUS_CT200H", VehicleModel::LEXUS_CT200H)
        .value("KIA_SORENTO", VehicleModel::KIA_SORENTO)
        .value("KIA_SPORTAGE", VehicleModel::KIA_SPORTAGE)
        .value("AUDI_Q7", VehicleModel::AUDI_Q7)
        .value("AUDI_A8L", VehicleModel::AUDI_A8L)
        .value("TESLA_MODEL_X", VehicleModel::TESLA_MODEL_X)
        .value("TESLA_MODEL_3", VehicleModel::TESLA_MODEL_3)
        .value("HYUNDAI_ELANTRA", VehicleModel::HYUNDAI_ELANTRA)
        .value("PEUGEOT_206", VehicleModel::PEUGEOT_206)
        .value("MAN_TGX", VehicleModel::MAN_TGX)
        .value("FACTION", VehicleModel::FACTION)
        .value("LINCOLN_MKZ", VehicleModel::LINCOLN_MKZ)
        .value("BMW_7", VehicleModel::BMW_7);

    class_<VehicleDetails>("VehicleDetails")
        .constructor<>()
        .property("vehicle_model", &VehicleDetails::vehicle_model)
        .property("wheelbase_m", &VehicleDetails::wheelbase_m)
        .property("front_track_width_m", &VehicleDetails::front_track_width_m)
        .property("rear_track_width_m", &VehicleDetails::rear_track_width_m)
        .STRUCT_FUNCTIONS(VehicleDetails);

    enum_<WheelSensorType>("WheelSensorType")
        .value("NONE", WheelSensorType::NONE)
        .value("TICK_RATE", WheelSensorType::TICK_RATE)
        .value("TICKS", WheelSensorType::TICKS)
        .value("WHEEL_SPEED", WheelSensorType::WHEEL_SPEED)
        .value("VEHICLE_SPEED", WheelSensorType::VEHICLE_SPEED)
        .value("VEHICLE_TICKS", WheelSensorType::VEHICLE_TICKS);

    enum_<AppliedSpeedType>("AppliedSpeedType")
        .value("NONE", AppliedSpeedType::NONE)
        .value("REAR_WHEELS", AppliedSpeedType::REAR_WHEELS)
        .value("FRONT_WHEELS", AppliedSpeedType::FRONT_WHEELS)
        .value("FRONT_AND_REAR_WHEELS", AppliedSpeedType::FRONT_AND_REAR_WHEELS)
        .value("VEHICLE_BODY", AppliedSpeedType::VEHICLE_BODY);

    enum_<SteeringType>("SteeringType")
        .value("UNKNOWN", SteeringType::UNKNOWN)
        .value("FRONT", SteeringType::FRONT)
        .value("FRONT_AND_REAR", SteeringType::FRONT_AND_REAR);

    class_<WheelConfig>("WheelConfig")
        .constructor<>()
        .property("wheel_sensor_type", &WheelConfig::wheel_sensor_type)
        .property("applied_speed_type", &WheelConfig::applied_speed_type)
        .property("steering_type", &WheelConfig::steering_type)
        .property("wheel_update_interval_sec", &WheelConfig::wheel_update_interval_sec)
        .property("wheel_tick_output_interval_sec", &WheelConfig::wheel_tick_output_interval_sec)
        .property("steering_ratio", &WheelConfig::steering_ratio)
        .property("wheel_ticks_to_m", &WheelConfig::wheel_ticks_to_m)
        .property("wheel_tick_max_value", &WheelConfig::wheel_tick_max_value)
        .property("wheel_ticks_signed", &WheelConfig::wheel_ticks_signed)
        .property("wheel_ticks_always_increase", &WheelConfig::wheel_ticks_always_increase)
        .STRUCT_FUNCTIONS(WheelConfig);

    enum_<TickMode>("TickMode")
        .value("OFF", TickMode::OFF)
        .value("RISING_EDGE", TickMode::RISING_EDGE)
        .value("FALLING_EDGE", TickMode::FALLING_EDGE);

    enum_<TickDirection>("TickDirection")
        .value("OFF", TickDirection::OFF)
        .value("FORWARD_ACTIVE_HIGH", TickDirection::FORWARD_ACTIVE_HIGH)
        .value("FORWARD_ACTIVE_LOW", TickDirection::FORWARD_ACTIVE_LOW);

    class_<HardwareTickConfig>("HardwareTickConfig")
        .constructor<>()
        .property("tick_mode", &HardwareTickConfig::tick_mode)
        .property("tick_direction", &HardwareTickConfig::tick_direction)
        .property("wheel_ticks_to_m", &HardwareTickConfig::wheel_ticks_to_m)
        .STRUCT_FUNCTIONS(HardwareTickConfig);

    enum_<ProtocolType>("ProtocolType")
        .value("INVALID", ProtocolType::INVALID)
        .value("FUSION_ENGINE", ProtocolType::FUSION_ENGINE)
        .value("NMEA", ProtocolType::NMEA)
        .value("RTCM", ProtocolType::RTCM);

    class_<MsgType>("MsgType")
        .constructor<>()
        .property("protocol", &MsgType::protocol)
        .property("msg_id", &MsgType::msg_id)
        .STRUCT_FUNCTIONS(MsgType);

    static auto MsgRate_MAX_RATE = MsgRate::MAX_RATE;
    class_<MsgRate>("MsgRate")
        .constructor<>()
        .class_property("MAX_RATE", &MsgRate_MAX_RATE)
        .property("type", &MsgRate::type)
        .property("update_period_ms", &MsgRate::update_period_ms)
        .STRUCT_FUNCTIONS(MsgRate);
}
