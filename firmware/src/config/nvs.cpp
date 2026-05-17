#include "config/nvs.h"
#include <Preferences.h>
#include "util/log.h"

namespace {
  constexpr const char* NS = "tdisp";
}

namespace nvs_config {

bool load(NvsConfig& out) {
  Preferences p;
  if (!p.begin(NS, true)) {
    LOG_WARN("nvs begin (ro) failed");
    return false;
  }
  out.wifi_ssid = p.getString("wifi_ssid", "");
  out.wifi_pass = p.getString("wifi_pass", "");
  out.last_screen_idx = p.getUChar("last_screen", 0);
  out.mqtt_reconnect_count = p.getULong("mqtt_reconn", 0);
  p.end();
  return true;
}

bool save_wifi(const String& ssid, const String& pass) {
  Preferences p;
  if (!p.begin(NS, false)) return false;
  p.putString("wifi_ssid", ssid);
  p.putString("wifi_pass", pass);
  p.end();
  LOG_INFO("nvs: saved wifi creds for ssid=%s", ssid.c_str());
  return true;
}

bool save_last_screen(uint8_t idx) {
  Preferences p;
  if (!p.begin(NS, false)) return false;
  p.putUChar("last_screen", idx);
  p.end();
  return true;
}

bool save_reconnect_count(uint32_t cnt) {
  Preferences p;
  if (!p.begin(NS, false)) return false;
  p.putULong("mqtt_reconn", cnt);
  p.end();
  return true;
}

bool erase_all() {
  Preferences p;
  if (!p.begin(NS, false)) return false;
  p.clear();
  p.end();
  LOG_WARN("nvs: cleared all keys");
  return true;
}

}  // namespace nvs_config
