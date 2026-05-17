#include "config/provisioning.h"
#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include "config/nvs.h"
#include "util/log.h"

namespace {
  constexpr const char* AP_SSID = "tdisplay-setup";
  constexpr const char* AP_PASS = "tdisplay";
  constexpr uint16_t DNS_PORT = 53;
  constexpr unsigned long TIMEOUT_MS = 10UL * 60UL * 1000UL;  // 10 min
}

namespace provisioning {

bool run_ap_fallback() {
  LOG_WARN("starting AP fallback: %s", AP_SSID);
  WiFi.disconnect(true);
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS);

  IPAddress ip = WiFi.softAPIP();
  LOG_INFO("AP IP: %s", ip.toString().c_str());

  DNSServer dns;
  dns.setErrorReplyCode(DNSReplyCode::NoError);
  dns.start(DNS_PORT, "*", ip);

  WebServer server(80);
  bool saved = false;
  String submitted_ssid, submitted_pass;

  server.on("/", HTTP_GET, [&]() {
    // Placeholder HTML — Task 11 expande
    server.send(200, "text/html",
      "<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'>"
      "<style>body{font-family:monospace;background:#000814;color:#E0F2FF;padding:20px}"
      "input{background:#001D3D;color:#E0F2FF;border:1px solid #00F5FF;padding:8px;width:100%;margin:8px 0}"
      "button{background:#00F5FF;color:#000;padding:10px 16px;border:none;cursor:pointer}</style>"
      "<h1>T-DISPLAY :: SETUP</h1>"
      "<form method=post action=/save>"
      "<label>SSID</label><input name=ssid required>"
      "<label>Password</label><input name=pass type=password>"
      "<button>SALVAR</button></form>");
  });

  server.on("/save", HTTP_POST, [&]() {
    submitted_ssid = server.arg("ssid");
    submitted_pass = server.arg("pass");
    if (submitted_ssid.length() == 0) {
      server.send(400, "text/plain", "ssid required");
      return;
    }
    nvs_config::save_wifi(submitted_ssid, submitted_pass);
    saved = true;
    server.send(200, "text/html",
      "<!doctype html><body style='background:#000814;color:#00FF85;font-family:monospace;padding:20px'>"
      "<h1>SALVO. REINICIANDO...</h1></body>");
  });

  server.onNotFound([&]() { server.send(200, "text/html", "<a href='http://192.168.4.1'>setup</a>"); });
  server.begin();

  unsigned long start = millis();
  while (!saved && (millis() - start) < TIMEOUT_MS) {
    dns.processNextRequest();
    server.handleClient();
    delay(10);
  }

  server.stop();
  dns.stop();
  WiFi.softAPdisconnect(true);
  WiFi.mode(WIFI_STA);

  return saved;
}

}  // namespace provisioning
