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

#define CHLID_ACCESSOR_WITH_OFFSET(name, cls, max_field, child_cls, \
                                   offset_bytes)                    \
  function(name,                                                    \
           select_overload<child_cls*(cls&, size_t)>(               \
               [](cls& message, size_t index) -> child_cls* {       \
                 if (index >= message.max_field) {                  \
                   return nullptr;                                  \
                 } else {                                           \
                   return &reinterpret_cast<child_cls*>(            \
                       reinterpret_cast<uint8_t*>(&message + 1) +   \
                       offset_bytes)[index];                        \
                 }                                                  \
               }),                                                  \
           allow_raw_pointer<child_cls*>())

#define CHLID_ACCESSOR(name, cls, max_field, child_cls) \
  CHLID_ACCESSOR_WITH_OFFSET(name, cls, max_field, child_cls, 0)

#define PARSE_FUNCTION(type)                                              \
  class_function(                                                         \
      "Parse",                                                            \
      select_overload<type*(const emscripten::val&, size_t)>(             \
          [](const emscripten::val& buffer, size_t size_bytes) -> type* { \
            if (size_bytes < sizeof(type)) {                              \
              return nullptr;                                             \
            } else {                                                      \
              return reinterpret_cast<type*>(buffer.as<size_t>());        \
            }                                                             \
          }),                                                             \
      allow_raw_pointer<type*>())

#define SIZEOF_FUNCTION(type) \
  class_function("SizeOf",    \
                 select_overload<size_t()>([]() { return sizeof(type); }))
