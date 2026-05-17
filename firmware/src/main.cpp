#include <Arduino.h>
#include <lvgl.h>
#include "util/log.h"
#include "display/driver.h"
#include "display/lvgl_setup.h"

void setup() {
  Serial.begin(115200);
  delay(800);
  LOG_INFO("=== T-Display-S3 dashboard boot ===");

  auto* gfx = display_driver::setup();
  if (!gfx) { while (true) delay(1000); }

  if (!lvgl_setup::init(gfx)) { while (true) delay(1000); }

  // Smoke test: label centralizado
  lv_obj_t* label = lv_label_create(lv_screen_active());
  lv_label_set_text(label, "T-DISPLAY :: HELLO\nCyberdeck booting...");
  lv_obj_set_style_text_color(label, lv_color_hex(0x00F5FF), 0);
  lv_obj_align(label, LV_ALIGN_CENTER, 0, 0);
  lv_obj_set_style_text_align(label, LV_TEXT_ALIGN_CENTER, 0);
}

void loop() {
  static uint32_t last = 0;
  uint32_t now = millis();
  uint32_t elapsed = now - last;
  last = now;
  lvgl_setup::tick_ms(elapsed);
  delay(5);
}
