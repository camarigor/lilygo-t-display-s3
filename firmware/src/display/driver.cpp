#include "display/driver.h"
#include "util/log.h"

namespace display_driver {

static Arduino_DataBus* g_bus = nullptr;
static Arduino_GFX* g_gfx = nullptr;

Arduino_GFX* setup() {
  // POWER_ON deve subir ANTES de qualquer comunicação com o painel
  pinMode(PIN_PWR, OUTPUT);
  digitalWrite(PIN_PWR, HIGH);
  delay(50);

  pinMode(PIN_BL, OUTPUT);
  digitalWrite(PIN_BL, LOW);

  // Bus: Arduino_ESP32PAR8Q é o driver i80 paralelo otimizado pra ESP32-S3
  // do T-Display-S3 (não Arduino_ESP32LCD8, que é genérico e não funciona
  // com esse painel). Conforme LilyGo official example Arduino_GFXDemo.
  g_bus = new Arduino_ESP32PAR8Q(
    PIN_DC, PIN_CS, PIN_WR, PIN_RD,
    PIN_D0, PIN_D1, PIN_D2, PIN_D3, PIN_D4, PIN_D5, PIN_D6, PIN_D7
  );

  // Constructor com rotation=0 (portrait native 170×320), offsets fixos
  // pro painel ST7789 com col_offset=35. setRotation(1) DEPOIS de begin()
  // remappeia coords pra landscape 320×170.
  g_gfx = new Arduino_ST7789(
    g_bus, PIN_RST,
    0 /*rotation portrait*/, true /*ips*/, 170, 320,
    35, 0, 35, 0  // col_offset1, row_offset1, col_offset2, row_offset2
  );

  if (!g_gfx->begin()) {
    LOG_ERROR("display begin failed");
    return nullptr;
  }
  g_gfx->setRotation(1);          // landscape após begin
  g_gfx->invertDisplay(true);     // painel é "negative" — sem invert, cores ficam pálidas
  g_gfx->fillScreen(0x0000);      // RGB565 black
  backlight_on();
  LOG_INFO("display init OK: %dx%d", WIDTH, HEIGHT);
  return g_gfx;
}

void backlight_on() { digitalWrite(PIN_BL, HIGH); }
void backlight_off() { digitalWrite(PIN_BL, LOW); }

}  // namespace display_driver
