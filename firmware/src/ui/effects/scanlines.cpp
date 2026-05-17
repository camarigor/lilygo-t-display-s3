#include "ui/effects/scanlines.h"
#include "ui/theme.h"
#include "display/driver.h"
#include <esp_heap_caps.h>

namespace scanlines {

static lv_obj_t* s_overlay = nullptr;
static lv_image_dsc_t s_dsc = {};
static lv_color_t* s_buf = nullptr;

void apply_overlay(lv_obj_t* parent_layer) {
  if (s_overlay) return;

  const int W = display_driver::WIDTH;
  const int H = display_driver::HEIGHT;
  const size_t bytes = W * H * sizeof(lv_color_t);
  s_buf = (lv_color_t*) heap_caps_calloc(1, bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (!s_buf) return;

  // Pinta linhas horizontais a cada 2 rows com cor cyan
  lv_color_t scanline_color = theme::color(theme::COLOR_ACCENT_CYAN);
  for (int y = 0; y < H; y += 2) {
    for (int x = 0; x < W; x++) {
      s_buf[y * W + x] = scanline_color;
    }
  }

  s_dsc.header.cf = LV_COLOR_FORMAT_RGB565;
  s_dsc.header.w = W;
  s_dsc.header.h = H;
  s_dsc.data_size = bytes;
  s_dsc.data = (const uint8_t*) s_buf;

  s_overlay = lv_image_create(parent_layer);
  lv_image_set_src(s_overlay, &s_dsc);
  lv_obj_set_style_opa(s_overlay, LV_OPA_20, 0);  // ~8% opacity sutil
  lv_obj_add_flag(s_overlay, LV_OBJ_FLAG_IGNORE_LAYOUT);
  lv_obj_align(s_overlay, LV_ALIGN_TOP_LEFT, 0, 0);
}

}  // namespace scanlines
