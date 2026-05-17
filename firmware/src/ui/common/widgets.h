#pragma once

#include <lvgl.h>

namespace widgets {
  // Cria barra horizontal preenchida com chars unicode █░ (16 segmentos).
  // pct: 0-100. cor segue threshold via theme::color_for_pct.
  lv_obj_t* create_bar_gauge(lv_obj_t* parent, float pct, int width_px);

  // Atualiza um bar_gauge existente.
  void update_bar_gauge(lv_obj_t* bar, float pct);

  // Status dot com glow (renderizado como label "●" + shadow).
  lv_obj_t* create_status_dot(lv_obj_t* parent, uint32_t color_hex);
  void set_status_dot_color(lv_obj_t* dot, uint32_t color_hex);

  // Border ASCII line-drawing envolvendo um container — implementação V1
  // usa lv_obj border simples (futuras versões podem swap pra labels com
  // chars unicode ═║╔╗╚╝).
  lv_obj_t* create_ascii_border(lv_obj_t* parent, int w, int h, uint32_t color_hex);
}
