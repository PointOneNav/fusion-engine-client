/**************************************************************************/ /**
 * @brief Emscripten bindings for the FusionEngineFramer class.
 ******************************************************************************/

#include <emscripten/bind.h>
#include <emscripten/emscripten.h>

#include <point_one/fusion_engine/parsers/fusion_engine_framer.h>

using namespace emscripten;
using namespace point_one::fusion_engine::parsers;

EMSCRIPTEN_BINDINGS(bindings) {
  class_<FusionEngineFramer>("FusionEngineFramer")
    .constructor<>()
    ;
}
