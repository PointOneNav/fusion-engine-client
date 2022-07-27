/**************************************************************************/ /**
 * @brief Emscripten binding helper functions.
 ******************************************************************************/

#include <emscripten/val.h>

#pragma once

#define ARRAY_PROPERTY(cls, member)                                        \
  property<emscripten::val>(#member, [](const cls& object) {               \
    return emscripten::val::array(                                         \
        object.member,                                                     \
        object.member + (sizeof(object.member) / sizeof(*object.member))); \
  })

#define DEFINE_PARSE_FUNCTION(type)                                                   \
  static const type* Parse##type(const emscripten::val& buffer, size_t size) { \
    if (size < sizeof(type)) {                                                 \
      return nullptr;                                                          \
    } else {                                                                   \
      return reinterpret_cast<const type*>(buffer.as<size_t>());               \
    }                                                                          \
  }

#define PARSE_FUNCTION(type) \
  class_function("Parse", &Parse##type, allow_raw_pointer<type*>())
