#pragma once

#include <Arduino.h>

// Níveis e macros simples (sem implementação de níveis runtime — DEBUG_LOG via build flag)

#define LOG_PRINTF(prefix, fmt, ...) \
    Serial.printf("[%lu][" prefix "] " fmt "\n", millis(), ##__VA_ARGS__)

#define LOG_INFO(fmt, ...)  LOG_PRINTF("INFO",  fmt, ##__VA_ARGS__)
#define LOG_WARN(fmt, ...)  LOG_PRINTF("WARN",  fmt, ##__VA_ARGS__)
#define LOG_ERROR(fmt, ...) LOG_PRINTF("ERROR", fmt, ##__VA_ARGS__)

#ifdef DEBUG_LOG
  #define LOG_DEBUG(fmt, ...) LOG_PRINTF("DEBUG", fmt, ##__VA_ARGS__)
#else
  #define LOG_DEBUG(fmt, ...) ((void)0)
#endif
