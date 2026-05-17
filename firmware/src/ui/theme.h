#pragma once

#include <lvgl.h>

// Fontes externas declaradas (geradas pela LVGL Font Converter; adicionadas em Task 5)
LV_FONT_DECLARE(vt323_14);
LV_FONT_DECLARE(vt323_18);
LV_FONT_DECLARE(vt323_24);
LV_FONT_DECLARE(vt323_32);
LV_FONT_DECLARE(vt323_48);
LV_FONT_DECLARE(press_start_24);

namespace theme {
  // Paleta Cyberdeck
  constexpr uint32_t COLOR_BG_DEEP        = 0x000814;
  constexpr uint32_t COLOR_BG_CARD        = 0x001D3D;
  constexpr uint32_t COLOR_BORDER_CRT     = 0x003566;
  constexpr uint32_t COLOR_TEXT_PRIMARY   = 0xE0F2FF;
  constexpr uint32_t COLOR_TEXT_SECONDARY = 0x7AA5C7;
  constexpr uint32_t COLOR_TEXT_DIM       = 0x3A5A7A;
  constexpr uint32_t COLOR_ACCENT_CYAN    = 0x00F5FF;
  constexpr uint32_t COLOR_ACCENT_MAGENTA = 0xFF00FF;
  constexpr uint32_t COLOR_ACCENT_GREEN   = 0x00FF85;
  constexpr uint32_t COLOR_ACCENT_AMBER   = 0xFFB627;
  constexpr uint32_t COLOR_ACCENT_RED     = 0xFF003C;

  // Helpers cor por threshold (verde<60%, amber<85%, red>=85%)
  inline uint32_t color_for_pct(float pct) {
    if (pct >= 85.0f) return COLOR_ACCENT_RED;
    if (pct >= 60.0f) return COLOR_ACCENT_AMBER;
    return COLOR_ACCENT_GREEN;
  }

  void apply_to_active_screen(lv_obj_t* scr);
  lv_color_t color(uint32_t hex);
}
