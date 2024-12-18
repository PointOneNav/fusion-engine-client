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
      .value("DEPRECATED_HEADING_BIAS", ConfigType::DEPRECATED_HEADING_BIAS)
      .value("GNSS_AUX_LEVER_ARM", ConfigType::GNSS_AUX_LEVER_ARM)
      .value("ENABLED_GNSS_SYSTEMS", ConfigType::ENABLED_GNSS_SYSTEMS)
      .value("ENABLED_GNSS_FREQUENCY_BANDS",
             ConfigType::ENABLED_GNSS_FREQUENCY_BANDS)
      .value("LEAP_SECOND", ConfigType::LEAP_SECOND)
      .value("GPS_WEEK_ROLLOVER", ConfigType::GPS_WEEK_ROLLOVER)
      .value("IONOSPHERE_CONFIG", ConfigType::IONOSPHERE_CONFIG)
      .value("TROPOSPHERE_CONFIG", ConfigType::TROPOSPHERE_CONFIG)
      .value("INTERFACE_CONFIG", ConfigType::INTERFACE_CONFIG)
      .value("UART1_BAUD", ConfigType::UART1_BAUD)
      .value("UART2_BAUD", ConfigType::UART2_BAUD)
      .value("UART1_OUTPUT_DIAGNOSTICS_MESSAGES",
             ConfigType::UART1_OUTPUT_DIAGNOSTICS_MESSAGES)
      .value("UART2_OUTPUT_DIAGNOSTICS_MESSAGES",
             ConfigType::UART2_OUTPUT_DIAGNOSTICS_MESSAGES)
      .value("ENABLE_WATCHDOG_TIMER", ConfigType::ENABLE_WATCHDOG_TIMER)
      .value("USER_DEVICE_ID", ConfigType::USER_DEVICE_ID)
      .value("LBAND_PARAMETERS", ConfigType::LBAND_PARAMETERS);

  enum_<ConfigurationSource>("ConfigurationSource")
      .value("ACTIVE", ConfigurationSource::ACTIVE)
      .value("SAVED", ConfigurationSource::SAVED)
      .value("DEFAULT", ConfigurationSource::DEFAULT);

  enum_<SaveAction>("SaveAction")
      .value("SAVE", SaveAction::SAVE)
      .value("REVERT_TO_SAVED", SaveAction::REVERT_TO_SAVED)
      .value("REVERT_TO_DEFAULT", SaveAction::REVERT_TO_DEFAULT);

  static auto SetConfigMessage_MESSAGE_TYPE = SetConfigMessage::MESSAGE_TYPE;
  static auto SetConfigMessage_MESSAGE_VERSION =
      SetConfigMessage::MESSAGE_VERSION;
  static auto SetConfigMessage_FLAG_APPLY_AND_SAVE =
      SetConfigMessage::FLAG_APPLY_AND_SAVE;
  static auto SetConfigMessage_FLAG_REVERT_TO_DEFAULT =
      SetConfigMessage::FLAG_REVERT_TO_DEFAULT;
  class_<SetConfigMessage>("SetConfigMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &SetConfigMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &SetConfigMessage_MESSAGE_VERSION)
      .class_property("FLAG_APPLY_AND_SAVE",
                      &SetConfigMessage_FLAG_APPLY_AND_SAVE)
      .class_property("FLAG_APPLY_AND_SAVE",
                      &SetConfigMessage_FLAG_APPLY_AND_SAVE)
      .property("config_type", &SetConfigMessage::config_type)
      .property("flags", &SetConfigMessage::flags)
      .ARRAY_PROPERTY(SetConfigMessage, reserved)
      .property("config_length_bytes", &SetConfigMessage::config_length_bytes)
      .STRUCT_FUNCTIONS(SetConfigMessage);

  static auto GetConfigMessage_MESSAGE_TYPE = GetConfigMessage::MESSAGE_TYPE;
  static auto GetConfigMessage_MESSAGE_VERSION =
      GetConfigMessage::MESSAGE_VERSION;
  class_<GetConfigMessage>("GetConfigMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &GetConfigMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &GetConfigMessage_MESSAGE_VERSION)
      .property("config_type", &GetConfigMessage::config_type)
      .property("request_source", &GetConfigMessage::request_source)
      .ARRAY_PROPERTY(GetConfigMessage, reserved)
      .STRUCT_FUNCTIONS(GetConfigMessage);

  static auto SaveConfigMessage_MESSAGE_TYPE = SaveConfigMessage::MESSAGE_TYPE;
  static auto SaveConfigMessage_MESSAGE_VERSION =
      SaveConfigMessage::MESSAGE_VERSION;
  class_<SaveConfigMessage>("SaveConfigMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &SaveConfigMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &SaveConfigMessage_MESSAGE_VERSION)
      .property("action", &SaveConfigMessage::action)
      .ARRAY_PROPERTY(SaveConfigMessage, reserved)
      .STRUCT_FUNCTIONS(SaveConfigMessage);

  static auto ConfigResponseMessage_MESSAGE_TYPE =
      ConfigResponseMessage::MESSAGE_TYPE;
  static auto ConfigResponseMessage_MESSAGE_VERSION =
      ConfigResponseMessage::MESSAGE_VERSION;
  static auto ConfigResponseMessage_FLAG_ACTIVE_DIFFERS_FROM_SAVED =
      ConfigResponseMessage::FLAG_ACTIVE_DIFFERS_FROM_SAVED;
  class_<ConfigResponseMessage>("ConfigResponseMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &ConfigResponseMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &ConfigResponseMessage_MESSAGE_VERSION)
      .class_property("FLAG_ACTIVE_DIFFERS_FROM_SAVED",
                      &ConfigResponseMessage_FLAG_ACTIVE_DIFFERS_FROM_SAVED)
      .property("config_source", &ConfigResponseMessage::config_source)
      .property("flags", &ConfigResponseMessage::flags)
      .property("config_type", &ConfigResponseMessage::config_type)
      .property("response", &ConfigResponseMessage::response)
      .ARRAY_PROPERTY(ConfigResponseMessage, reserved)
      .property("config_length_bytes",
                &ConfigResponseMessage::config_length_bytes)
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
      .value("FACTION_V2", VehicleModel::FACTION_V2)
      .value("LINCOLN_MKZ", VehicleModel::LINCOLN_MKZ)
      .value("BMW_7", VehicleModel::BMW_7)
      .value("BMW_MOTORRAD", VehicleModel::BMW_MOTORRAD)
      .value("VW_4", VehicleModel::VW_4)
      .value("RIVIAN", VehicleModel::RIVIAN);

  class_<VehicleDetails>("VehicleDetails")
      .constructor<>()
      .property("vehicle_model", &VehicleDetails::vehicle_model)
      .ARRAY_PROPERTY(VehicleDetails, reserved)
      .property("wheelbase_m", &VehicleDetails::wheelbase_m)
      .property("front_track_width_m", &VehicleDetails::front_track_width_m)
      .property("rear_track_width_m", &VehicleDetails::rear_track_width_m)
      .STRUCT_FUNCTIONS(VehicleDetails);

  enum_<WheelSensorType>("WheelSensorType")
      .value("NONE", WheelSensorType::NONE)
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
      .ARRAY_PROPERTY(WheelConfig, reserved1)
      .property("wheel_update_interval_sec",
                &WheelConfig::wheel_update_interval_sec)
      .property("wheel_tick_output_interval_sec",
                &WheelConfig::wheel_tick_output_interval_sec)
      .property("steering_ratio", &WheelConfig::steering_ratio)
      .property("wheel_ticks_to_m", &WheelConfig::wheel_ticks_to_m)
      .property("wheel_tick_max_value", &WheelConfig::wheel_tick_max_value)
      .property("wheel_ticks_signed", &WheelConfig::wheel_ticks_signed)
      .property("wheel_ticks_always_increase",
                &WheelConfig::wheel_ticks_always_increase)
      .ARRAY_PROPERTY(WheelConfig, reserved2)
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
      .ARRAY_PROPERTY(HardwareTickConfig, reserved1)
      .property("wheel_ticks_to_m", &HardwareTickConfig::wheel_ticks_to_m)
      .STRUCT_FUNCTIONS(HardwareTickConfig);

  enum_<IonoDelayModel>("IonoDelayModel")
      .value("AUTO", IonoDelayModel::AUTO)
      .value("OFF", IonoDelayModel::OFF)
      .value("KLOBUCHAR", IonoDelayModel::KLOBUCHAR)
      .value("SBAS", IonoDelayModel::SBAS);

  class_<IonosphereConfig>("IonosphereConfig")
      .constructor<>()
      .property("iono_delay_model", &IonosphereConfig::iono_delay_model)
      .ARRAY_PROPERTY(IonosphereConfig, reserved)
      .STRUCT_FUNCTIONS(IonosphereConfig);

  enum_<TropoDelayModel>("TropoDelayModel")
      .value("AUTO", TropoDelayModel::AUTO)
      .value("OFF", TropoDelayModel::OFF)
      .value("SAASTAMOINEN", TropoDelayModel::SAASTAMOINEN);

  class_<TroposphereConfig>("TroposphereConfig")
      .constructor<>()
      .property("tropo_delay_model", &TroposphereConfig::tropo_delay_model)
      .ARRAY_PROPERTY(TroposphereConfig, reserved)
      .STRUCT_FUNCTIONS(TroposphereConfig);

  enum_<DataType>("DataType")
      .value("CALIBRATION_STATE", DataType::CALIBRATION_STATE)
      .value("CRASH_LOG", DataType::CRASH_LOG)
      .value("FILTER_STATE", DataType::FILTER_STATE)
      .value("USER_CONFIG", DataType::USER_CONFIG)
      .value("INVALID", DataType::INVALID);

  static auto ImportDataMessage_MESSAGE_TYPE = ImportDataMessage::MESSAGE_TYPE;
  static auto ImportDataMessage_MESSAGE_VERSION =
      ImportDataMessage::MESSAGE_VERSION;
  class_<ImportDataMessage>("ImportDataMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &ImportDataMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &ImportDataMessage_MESSAGE_VERSION)
      .property("data_type", &ImportDataMessage::data_type)
      .property("source", &ImportDataMessage::source)
      .ARRAY_PROPERTY(ImportDataMessage, reserved1)
      .property("data_version", &ImportDataMessage::data_version)
      .ARRAY_PROPERTY(ImportDataMessage, reserved2)
      .property("data_length_bytes", &ImportDataMessage::data_length_bytes)
      .STRUCT_FUNCTIONS(ImportDataMessage);

  static auto ExportDataMessage_MESSAGE_TYPE = ExportDataMessage::MESSAGE_TYPE;
  static auto ExportDataMessage_MESSAGE_VERSION =
      ExportDataMessage::MESSAGE_VERSION;
  class_<ExportDataMessage>("ExportDataMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &ExportDataMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &ExportDataMessage_MESSAGE_VERSION)
      .property("data_type", &ExportDataMessage::data_type)
      .property("source", &ExportDataMessage::source)
      .ARRAY_PROPERTY(ExportDataMessage, reserved)
      .STRUCT_FUNCTIONS(ExportDataMessage);

  static auto PlatformStorageDataMessage_MESSAGE_TYPE =
      PlatformStorageDataMessage::MESSAGE_TYPE;
  static auto PlatformStorageDataMessage_MESSAGE_VERSION =
      PlatformStorageDataMessage::MESSAGE_VERSION;
  static auto
      PlatformStorageDataMessage_FLAG_USER_CONFIG_PLATFORM_NOT_SPECIFIED =
          PlatformStorageDataMessage::FLAG_USER_CONFIG_PLATFORM_NOT_SPECIFIED;
  static auto PlatformStorageDataMessage_FLAG_USER_CONFIG_PLATFORM_POSIX =
      PlatformStorageDataMessage::FLAG_USER_CONFIG_PLATFORM_POSIX;
  static auto PlatformStorageDataMessage_FLAG_USER_CONFIG_PLATFORM_EMBEDDED =
      PlatformStorageDataMessage::FLAG_USER_CONFIG_PLATFORM_EMBEDDED;
  static auto
      PlatformStorageDataMessage_FLAG_USER_CONFIG_PLATFORM_EMBEDDED_SSR =
          PlatformStorageDataMessage::FLAG_USER_CONFIG_PLATFORM_EMBEDDED_SSR;
  class_<PlatformStorageDataMessage>("PlatformStorageDataMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &PlatformStorageDataMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION",
                      &PlatformStorageDataMessage_MESSAGE_VERSION)
      .class_property(
          "FLAG_USER_CONFIG_PLATFORM_NOT_SPECIFIED",
          &PlatformStorageDataMessage_FLAG_USER_CONFIG_PLATFORM_NOT_SPECIFIED)
      .class_property(
          "FLAG_USER_CONFIG_PLATFORM_POSIX",
          &PlatformStorageDataMessage_FLAG_USER_CONFIG_PLATFORM_POSIX)
      .class_property(
          "FLAG_USER_CONFIG_PLATFORM_EMBEDDED",
          &PlatformStorageDataMessage_FLAG_USER_CONFIG_PLATFORM_EMBEDDED)
      .class_property(
          "FLAG_USER_CONFIG_PLATFORM_EMBEDDED_SSR",
          &PlatformStorageDataMessage_FLAG_USER_CONFIG_PLATFORM_EMBEDDED_SSR)
      .property("data_type", &PlatformStorageDataMessage::data_type)
      .property("response", &PlatformStorageDataMessage::response)
      .property("source", &PlatformStorageDataMessage::source)
      .property("flags", &PlatformStorageDataMessage::flags)
      .property("data_version", &PlatformStorageDataMessage::data_version)
      .property("data_length_bytes",
                &PlatformStorageDataMessage::data_length_bytes)
      .STRUCT_FUNCTIONS(PlatformStorageDataMessage);

  enum_<InterfaceConfigType>("InterfaceConfigType")
      .value("INVALID", InterfaceConfigType::INVALID)
      .value("OUTPUT_DIAGNOSTICS_MESSAGES",
             InterfaceConfigType::OUTPUT_DIAGNOSTICS_MESSAGES)
      .value("BAUD_RATE", InterfaceConfigType::BAUD_RATE)
      .value("REMOTE_ADDRESS", InterfaceConfigType::REMOTE_ADDRESS)
      .value("PORT", InterfaceConfigType::PORT)
      .value("ENABLED", InterfaceConfigType::ENABLED)
      .value("DIRECTION", InterfaceConfigType::DIRECTION)
      .value("SOCKET_TYPE", InterfaceConfigType::SOCKET_TYPE);

  enum_<ProtocolType>("ProtocolType")
      .value("INVALID", ProtocolType::INVALID)
      .value("FUSION_ENGINE", ProtocolType::FUSION_ENGINE)
      .value("NMEA", ProtocolType::NMEA)
      .value("RTCM", ProtocolType::RTCM)
      .value("ALL", ProtocolType::ALL);

  enum_<TransportType>("TransportType")
      .value("INVALID", TransportType::INVALID)
      .value("SERIAL", TransportType::SERIAL)
      .value("FILE", TransportType::FILE)
      .value("TCP", TransportType::TCP)
      .value("UDP", TransportType::UDP)
      .value("WEBSOCKET", TransportType::WEBSOCKET)
      .value("CURRENT", TransportType::CURRENT)
      .value("ALL", TransportType::ALL);

  enum_<TransportDirection>("TransportDirection")
      .value("INVALID", TransportDirection::INVALID)
      .value("SERVER", TransportDirection::SERVER)
      .value("CLIENT", TransportDirection::CLIENT);

  enum_<SocketType>("SocketType")
      .value("INVALID", SocketType::INVALID)
      .value("STREAM", SocketType::STREAM)
      .value("DATAGRAM", SocketType::DATAGRAM)
      .value("SEQPACKET", SocketType::SEQPACKET);

  class_<InterfaceID>("InterfaceID")
      .constructor<>()
      .property("type", &InterfaceID::type)
      .property("index", &InterfaceID::index)
      .ARRAY_PROPERTY(InterfaceID, reserved)
      .STRUCT_FUNCTIONS(InterfaceID);

  enum_<NmeaMessageType>("NmeaMessageType")
      .value("INVALID", NmeaMessageType::INVALID)
      .value("GGA", NmeaMessageType::GGA)
      .value("GLL", NmeaMessageType::GLL)
      .value("GSA", NmeaMessageType::GSA)
      .value("GSV", NmeaMessageType::GSV)
      .value("RMC", NmeaMessageType::RMC)
      .value("VTG", NmeaMessageType::VTG)
      .value("P1CALSTATUS", NmeaMessageType::P1CALSTATUS)
      .value("P1MSG", NmeaMessageType::P1MSG)
      .value("PQTMVERNO", NmeaMessageType::PQTMVERNO)
      .value("PQTMVER", NmeaMessageType::PQTMVER)
      .value("PQTMGNSS", NmeaMessageType::PQTMGNSS)
      .value("PQTMVERNO_SUB", NmeaMessageType::PQTMVERNO_SUB)
      .value("PQTMVER_SUB", NmeaMessageType::PQTMVER_SUB)
      .value("PQTMTXT", NmeaMessageType::PQTMTXT);

  enum_<MessageRate>("MessageRate")
      .value("OFF", MessageRate::OFF)
      .value("ON_CHANGE", MessageRate::ON_CHANGE)
      .value("MAX_RATE", MessageRate::MAX_RATE)
      .value("INTERVAL_10_MS", MessageRate::INTERVAL_10_MS)
      .value("INTERVAL_20_MS", MessageRate::INTERVAL_20_MS)
      .value("INTERVAL_40_MS", MessageRate::INTERVAL_40_MS)
      .value("INTERVAL_50_MS", MessageRate::INTERVAL_50_MS)
      .value("INTERVAL_100_MS", MessageRate::INTERVAL_100_MS)
      .value("INTERVAL_200_MS", MessageRate::INTERVAL_200_MS)
      .value("INTERVAL_500_MS", MessageRate::INTERVAL_500_MS)
      .value("INTERVAL_1_S", MessageRate::INTERVAL_1_S)
      .value("INTERVAL_2_S", MessageRate::INTERVAL_2_S)
      .value("INTERVAL_5_S", MessageRate::INTERVAL_5_S)
      .value("INTERVAL_10_S", MessageRate::INTERVAL_10_S)
      .value("INTERVAL_30_S", MessageRate::INTERVAL_30_S)
      .value("INTERVAL_60_S", MessageRate::INTERVAL_60_S)
      .value("DEFAULT", MessageRate::DEFAULT);

  class_<InterfaceConfigSubmessage>("InterfaceConfigSubmessage")
      .constructor<>()
      .property("interface", &InterfaceConfigSubmessage::interface)
      .property("subtype", &InterfaceConfigSubmessage::subtype)
      .ARRAY_PROPERTY(InterfaceConfigSubmessage, reserved)
      .STRUCT_FUNCTIONS(InterfaceConfigSubmessage);

  static auto SetMessageRate_MESSAGE_TYPE = SetMessageRate::MESSAGE_TYPE;
  static auto SetMessageRate_MESSAGE_VERSION = SetMessageRate::MESSAGE_VERSION;
  static auto SetMessageRate_FLAG_APPLY_AND_SAVE =
      SetMessageRate::FLAG_APPLY_AND_SAVE;
  static auto SetMessageRate_FLAG_INCLUDE_DISABLED_MESSAGES =
      SetMessageRate::FLAG_INCLUDE_DISABLED_MESSAGES;
  class_<SetMessageRate>("SetMessageRate")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &SetMessageRate_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &SetMessageRate_MESSAGE_VERSION)
      .class_property("FLAG_APPLY_AND_SAVE",
                      &SetMessageRate_FLAG_APPLY_AND_SAVE)
      .class_property("FLAG_INCLUDE_DISABLED_MESSAGES",
                      &SetMessageRate_FLAG_INCLUDE_DISABLED_MESSAGES)
      .property("output_interface", &SetMessageRate::output_interface)
      .property("protocol", &SetMessageRate::protocol)
      .property("flags", &SetMessageRate::flags)
      .property("message_id", &SetMessageRate::message_id)
      .property("rate", &SetMessageRate::rate)
      .ARRAY_PROPERTY(SetMessageRate, reserved2)
      .STRUCT_FUNCTIONS(SetMessageRate);

  static auto GetMessageRate_MESSAGE_TYPE = GetMessageRate::MESSAGE_TYPE;
  static auto GetMessageRate_MESSAGE_VERSION = GetMessageRate::MESSAGE_VERSION;
  class_<GetMessageRate>("GetMessageRate")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &GetMessageRate_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &GetMessageRate_MESSAGE_VERSION)
      .property("output_interface", &GetMessageRate::output_interface)
      .property("protocol", &GetMessageRate::protocol)
      .property("request_source", &GetMessageRate::request_source)
      .property("message_id", &GetMessageRate::message_id)
      .STRUCT_FUNCTIONS(GetMessageRate);

  static auto SupportedIOInterfacesMessage_MESSAGE_TYPE =
      SupportedIOInterfacesMessage::MESSAGE_TYPE;
  static auto SupportedIOInterfacesMessage_MESSAGE_VERSION =
      SupportedIOInterfacesMessage::MESSAGE_VERSION;
  class_<SupportedIOInterfacesMessage>("SupportedIOInterfacesMessage")
      .constructor<>()
      .class_property("MESSAGE_TYPE",
                      &SupportedIOInterfacesMessage_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION",
                      &SupportedIOInterfacesMessage_MESSAGE_VERSION)
      .property("num_interfaces", &SupportedIOInterfacesMessage::num_interfaces)
      .ARRAY_PROPERTY(SupportedIOInterfacesMessage, reserved1)
      .STRUCT_FUNCTIONS(SupportedIOInterfacesMessage);

  static auto MessageRateResponseEntry_FLAG_ACTIVE_DIFFERS_FROM_SAVED =
      MessageRateResponseEntry::FLAG_ACTIVE_DIFFERS_FROM_SAVED;
  class_<MessageRateResponseEntry>("MessageRateResponseEntry")
      .constructor<>()
      .class_property("FLAG_ACTIVE_DIFFERS_FROM_SAVED",
                      &MessageRateResponseEntry_FLAG_ACTIVE_DIFFERS_FROM_SAVED)
      .property("protocol", &MessageRateResponseEntry::protocol)
      .property("flags", &MessageRateResponseEntry::flags)
      .property("message_id", &MessageRateResponseEntry::message_id)
      .property("configured_rate", &MessageRateResponseEntry::configured_rate)
      .property("effective_rate", &MessageRateResponseEntry::effective_rate)
      .ARRAY_PROPERTY(MessageRateResponseEntry, reserved1)
      .STRUCT_FUNCTIONS(MessageRateResponseEntry);

  static auto MessageRateResponse_MESSAGE_TYPE =
      MessageRateResponse::MESSAGE_TYPE;
  static auto MessageRateResponse_MESSAGE_VERSION =
      MessageRateResponse::MESSAGE_VERSION;
  class_<MessageRateResponse>("MessageRateResponse")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &GetMessageRate_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &GetMessageRate_MESSAGE_VERSION)
      .property("config_source", &MessageRateResponse::config_source)
      .property("response", &MessageRateResponse::response)
      .property("num_rates", &MessageRateResponse::num_rates)
      .property("output_interface", &MessageRateResponse::output_interface)
      .STRUCT_FUNCTIONS(MessageRateResponse);

  class_<LBandConfig>("LBandConfig")
      .constructor<>()
      .property("center_frequency_hz", &LBandConfig::center_frequency_hz)
      .property("search_window_hz", &LBandConfig::search_window_hz)
      .property("filter_data_by_service_id",
                &LBandConfig::filter_data_by_service_id)
      .property("use_descrambler", &LBandConfig::use_descrambler)
      .property("pmp_service_id", &LBandConfig::pmp_service_id)
      .property("pmp_unique_word", &LBandConfig::pmp_unique_word)
      .property("pmp_data_rate_bps", &LBandConfig::pmp_data_rate_bps)
      .property("descrambler_init", &LBandConfig::descrambler_init)
      .STRUCT_FUNCTIONS(LBandConfig);
}
