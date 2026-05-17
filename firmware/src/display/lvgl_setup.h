#pragma once

#include <lvgl.h>
#include <Arduino_GFX_Library.h>

namespace lvgl_setup {
  bool init(Arduino_GFX* gfx);
  void tick_ms(uint32_t ms);   // chamado a cada loop()
}
