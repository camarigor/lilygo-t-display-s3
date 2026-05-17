#include "display/lvgl_setup.h"
#include "display/driver.h"
#include <esp_heap_caps.h>
#include "util/log.h"

namespace lvgl_setup {

static Arduino_GFX* s_gfx = nullptr;
static lv_color_t* s_buf1 = nullptr;
static lv_color_t* s_buf2 = nullptr;
static lv_display_t* s_disp = nullptr;

static constexpr size_t BUF_PIXELS = display_driver::WIDTH * display_driver::HEIGHT;  // 54400
static constexpr size_t BUF_BYTES  = BUF_PIXELS * sizeof(lv_color_t);                 // ~109KB

static void flush_cb(lv_display_t* disp, const lv_area_t* area, uint8_t* px_map) {
  uint16_t w = area->x2 - area->x1 + 1;
  uint16_t h = area->y2 - area->y1 + 1;
  s_gfx->draw16bitBeRGBBitmap(area->x1, area->y1, (uint16_t*)px_map, w, h);
  lv_display_flush_ready(disp);
}

bool init(Arduino_GFX* gfx) {
  s_gfx = gfx;
  lv_init();

  s_buf1 = (lv_color_t*) heap_caps_malloc(BUF_BYTES, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  s_buf2 = (lv_color_t*) heap_caps_malloc(BUF_BYTES, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (!s_buf1 || !s_buf2) {
    LOG_ERROR("lvgl alloc failed (psram free: %u)",
              (unsigned)heap_caps_get_free_size(MALLOC_CAP_SPIRAM));
    return false;
  }

  s_disp = lv_display_create(display_driver::WIDTH, display_driver::HEIGHT);
  lv_display_set_buffers(s_disp, s_buf1, s_buf2, BUF_BYTES, LV_DISPLAY_RENDER_MODE_PARTIAL);
  lv_display_set_flush_cb(s_disp, flush_cb);

  LOG_INFO("lvgl init OK: psram free=%uKB", (unsigned)heap_caps_get_free_size(MALLOC_CAP_SPIRAM) / 1024);
  return true;
}

void tick_ms(uint32_t ms) {
  lv_tick_inc(ms);
  lv_timer_handler();
}

}  // namespace lvgl_setup
