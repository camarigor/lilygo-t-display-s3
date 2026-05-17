#pragma once

#include <Arduino_GFX_Library.h>

namespace display_driver {
  // Largura/altura em paisagem
  constexpr int16_t WIDTH  = 320;
  constexpr int16_t HEIGHT = 170;

  // Pinos T-Display-S3 (i80 8-bit paralelo)
  constexpr int8_t PIN_D0 = 39;
  constexpr int8_t PIN_D1 = 40;
  constexpr int8_t PIN_D2 = 41;
  constexpr int8_t PIN_D3 = 42;
  constexpr int8_t PIN_D4 = 45;
  constexpr int8_t PIN_D5 = 46;
  constexpr int8_t PIN_D6 = 47;
  constexpr int8_t PIN_D7 = 48;
  constexpr int8_t PIN_WR = 8;
  constexpr int8_t PIN_RD = 9;
  constexpr int8_t PIN_DC = 7;
  constexpr int8_t PIN_CS = 6;
  constexpr int8_t PIN_RST = 5;
  constexpr int8_t PIN_BL = 38;
  constexpr int8_t PIN_PWR = 15;  // LCD_POWER_ON — mantém regulator do display ativo

  Arduino_GFX* setup();
  void backlight_on();
  void backlight_off();
}
