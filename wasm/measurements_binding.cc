/**************************************************************************/ /**
 * @brief Emscripten bindings for structs in measurements.h.
 ******************************************************************************/

#include <emscripten/bind.h>
#include <emscripten/emscripten.h>

#include <point_one/fusion_engine/messages/core.h>

#include "binding_utils.h"

using namespace emscripten;
using namespace point_one::fusion_engine::messages;

/******************************************************************************/
EMSCRIPTEN_BINDINGS(measurements) {
  static auto HeadingMeasurement_MESSAGE_TYPE =
      HeadingMeasurement::MESSAGE_TYPE;
  static auto HeadingMeasurement_MESSAGE_VERSION =
      HeadingMeasurement::MESSAGE_VERSION;
  class_<HeadingMeasurement>("HeadingMeasurement")
      .constructor<>()
      .class_property("MESSAGE_TYPE", &HeadingMeasurement_MESSAGE_TYPE)
      .class_property("MESSAGE_VERSION", &HeadingMeasurement_MESSAGE_VERSION)
      .property("timestamps", &HeadingMeasurement::timestamps)
      .property("solution_type", &HeadingMeasurement::solution_type)
      .ARRAY_PROPERTY(HeadingMeasurement, reserved)
      .property("flags", &HeadingMeasurement::flags)
      .ARRAY_PROPERTY(HeadingMeasurement, relative_position_enu_m)
      .ARRAY_PROPERTY(HeadingMeasurement, position_std_enu_m)
      .property("heading_true_north_deg",
                &HeadingMeasurement::heading_true_north_deg)
      .property("baseline_distance_m", &HeadingMeasurement::baseline_distance_m)
      .STRUCT_FUNCTIONS(HeadingMeasurement);
}
