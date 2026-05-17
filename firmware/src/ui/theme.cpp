#include "ui/theme.h"

namespace theme {

lv_color_t color(uint32_t hex) {
  return lv_color_hex(hex);
}

void apply_to_active_screen(lv_obj_t* scr) {
  lv_obj_set_style_bg_color(scr, color(COLOR_BG_DEEP), 0);
  lv_obj_set_style_bg_opa(scr, LV_OPA_COVER, 0);
  lv_obj_set_style_text_color(scr, color(COLOR_TEXT_PRIMARY), 0);
  lv_obj_set_style_text_font(scr, &vt323_18, 0);
}

}  // namespace theme
