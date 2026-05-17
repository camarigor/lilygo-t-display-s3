#pragma once

#include <Arduino.h>

namespace provisioning {
  // Sobe AP `tdisplay-setup` + servidor HTTP em 192.168.4.1 com captive portal.
  // Bloqueia até user submeter form OU timeout. Retorna true se SSID salvo em NVS.
  bool run_ap_fallback();
}
