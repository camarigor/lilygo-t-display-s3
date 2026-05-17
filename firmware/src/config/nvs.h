#pragma once

#include <Arduino.h>

struct NvsConfig {
  String wifi_ssid;
  String wifi_pass;
  uint8_t last_screen_idx = 0;
  uint32_t mqtt_reconnect_count = 0;
  bool valid() const { return wifi_ssid.length() > 0; }
};

namespace nvs_config {
  bool load(NvsConfig& out);
  bool save_wifi(const String& ssid, const String& pass);
  bool save_last_screen(uint8_t idx);
  bool save_reconnect_count(uint32_t cnt);
  bool erase_all();
}
