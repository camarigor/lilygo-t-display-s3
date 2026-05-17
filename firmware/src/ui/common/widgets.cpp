#include "ui/common/widgets.h"
#include "ui/theme.h"
#include <Arduino.h>

namespace widgets {

static String pct_to_bar(float pct) {
  // 16 segmentos. Cada segmento representa 6.25%.
  constexpr int N = 16;
  int full = (int)(pct / 6.25f);
  if (full > N) full = N;
  String s;
  for (int i = 0; i < full; i++)     s += "\xE2\x96\x88";   // █
  for (int i = 0; i < N - full; i++) s += "\xE2\x96\x91";   // ░
  return s;
}

lv_obj_t* create_bar_gauge(lv_obj_t* parent, float pct, int width_px) {
  lv_obj_t* label = lv_label_create(parent);
  String s = pct_to_bar(pct);
  lv_label_set_text(label, s.c_str());
  lv_obj_set_style_text_color(label, theme::color(theme::color_for_pct(pct)), 0);
  lv_obj_set_style_text_font(label, &vt323_18, 0);
  lv_obj_set_width(label, width_px);
  return label;
}

void update_bar_gauge(lv_obj_t* bar, float pct) {
  lv_label_set_text(bar, pct_to_bar(pct).c_str());
  lv_obj_set_style_text_color(bar, theme::color(theme::color_for_pct(pct)), 0);
}

lv_obj_t* create_status_dot(lv_obj_t* parent, uint32_t color_hex) {
  lv_obj_t* dot = lv_label_create(parent);
  lv_label_set_text(dot, "\xE2\x97\x8F");  // ●
  lv_obj_set_style_text_color(dot, theme::color(color_hex), 0);
  lv_obj_set_style_text_font(dot, &vt323_24, 0);
  // Glow via shadow
  lv_obj_set_style_shadow_color(dot, theme::color(color_hex), 0);
  lv_obj_set_style_shadow_width(dot, 8, 0);
  lv_obj_set_style_shadow_opa(dot, LV_OPA_80, 0);
  lv_obj_set_style_shadow_spread(dot, 2, 0);
  return dot;
}

void set_status_dot_color(lv_obj_t* dot, uint32_t color_hex) {
  lv_obj_set_style_text_color(dot, theme::color(color_hex), 0);
  lv_obj_set_style_shadow_color(dot, theme::color(color_hex), 0);
}

lv_obj_t* create_ascii_border(lv_obj_t* parent, int w, int h, uint32_t color_hex) {
  lv_obj_t* container = lv_obj_create(parent);
  lv_obj_set_size(container, w, h);
  lv_obj_set_style_bg_opa(container, LV_OPA_TRANSP, 0);
  lv_obj_set_style_pad_all(container, 0, 0);
  lv_obj_set_style_border_color(container, theme::color(color_hex), 0);
  lv_obj_set_style_border_width(container, 1, 0);
  lv_obj_set_style_border_opa(container, LV_OPA_50, 0);
  lv_obj_set_style_radius(container, 0, 0);
  return container;
}

}  // namespace widgets
