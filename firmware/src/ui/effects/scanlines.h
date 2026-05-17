#pragma once

#include <lvgl.h>

namespace scanlines {
  // Cria layer overlay com linhas horizontais 1px a cada 2px, opacity ~8%.
  // Adiciona como filho TOP do active screen (passar via parent_layer).
  void apply_overlay(lv_obj_t* parent_layer);
}
