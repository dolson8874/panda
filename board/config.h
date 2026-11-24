#pragma once

#include <stdbool.h>

#define CAN_INIT_TIMEOUT_MS 500U
#define USBPACKET_MAX_SIZE 0x40U
#if defined(STM32F4) && !defined(BOOTSTUB)
  #define USB_CAN_OUT_PACKET_COUNT 4U
  // Six bytes per minimum frame, including a possible frame continued from the previous window.
  #define MAX_CAN_MSGS_PER_USB_BULK_TRANSFER ((USB_CAN_OUT_PACKET_COUNT * USBPACKET_MAX_SIZE + CANPACKET_HEAD_SIZE - 1U) / CANPACKET_HEAD_SIZE)
#else
  #define USB_CAN_OUT_PACKET_COUNT 32U
  #define MAX_CAN_MSGS_PER_USB_BULK_TRANSFER 51U
#endif
#define MAX_CAN_MSGS_PER_SPI_BULK_TRANSFER 170U

// USB definitions
#define USB_VID 0x3801U

#ifdef BOOTSTUB
  #define USB_PID 0xDDEEU
#else
  #define USB_PID 0xDDCCU
#endif

// platform includes
#ifdef STM32H7
  #include "board/stm32h7/stm32h7_config.h"
#elif defined(STM32F4)
  #include "board/stm32f4/stm32f4_config.h"
#else
  // TODO: uncomment this, cppcheck complains
  // building for tests
  //#include "fake_stm.h"
#endif
