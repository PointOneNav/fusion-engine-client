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

#define PARSE_FUNCTION(type)                                              \
  class_function(                                                         \
      "Parse"#type,                                                      \
      select_overload<type*(const emscripten::val&, size_t)>(             \
          [](const emscripten::val& buffer, size_t size_bytes) -> type* { \
            if (size_bytes < sizeof(type)) {                              \
              return nullptr;                                             \
            } else {                                                      \
              return reinterpret_cast<type*>(buffer.as<size_t>());        \
            }                                                             \
          }),                                                             \
      allow_raw_pointer<type*>())
