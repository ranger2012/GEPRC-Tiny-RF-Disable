# GEPRC Tiny Radio — RF TX disabled (ExpressLRS 3.4.2)

This repository builds a modified ExpressLRS 3.4.2 firmware for the **DIY Mini ESP32 SX1280 2.4 GHz TX** target.

## What the patch changes

- Blocks SX1280 normal packet transmission in `SX1280Driver::TXnb()`.
- Blocks the continuous-wave RF test in `SX1280Driver::startCWTest()`.
- Calls the normal TX-completion handler when a packet is suppressed, so the firmware state machine can continue and schedule its receive/telemetry phase.
- Does not change the Wi-Fi web updater, SETUP button handling, or the serial/PPM interface code.

The build environment is `Unified_ESP32_2400_TX_via_UART`, which is the unified ESP32 2.4 GHz TX environment used by the DIY Mini target. Hardware pin assignments are runtime configuration; the supplied `hardware.json` is a backup of the user's existing settings and is not used to rewrite pins in the firmware build.

## Build

A GitHub Actions workflow builds the firmware automatically when this repository is updated, and can also be started manually from the Actions tab.

The workflow checks out upstream ExpressLRS tag `3.4.2`, applies the local RF-disable patch, and builds:

```
Unified_ESP32_2400_TX_via_UART
```

Download the ZIP from the successful workflow run's **Artifacts** section. It contains `firmware.bin` and the hardware configuration backup.

## Important

This is an experimental software modification. It has not been electrically tested on the GEPRC radio. Before relying on it, verify with suitable RF test equipment that no carrier or packets are emitted. Keep a known-good stock firmware available for recovery. Do not change the radio pin assignments or set the SX1280 NSS/SCK pins to -1.
