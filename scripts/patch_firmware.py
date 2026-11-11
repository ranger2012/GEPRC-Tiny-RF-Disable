#!/usr/bin/env python3
"""Patch ExpressLRS 3.4.2 to suppress SX1280 TX and unify NimBLE dependencies."""

from pathlib import Path
import re
import sys

source = Path("ExpressLRS/src/lib/SX1280Driver/SX1280.cpp")
if not source.is_file():
    raise SystemExit(f"Expected source file not found: {source}")

text = source.read_text(encoding="utf-8")


def replace_function(signature_fragment: str, replacement_body: str) -> None:
    global text
    start = text.find(signature_fragment)
    if start < 0:
        raise SystemExit(f"Could not find function: {signature_fragment}")
    if text.find(signature_fragment, start + 1) >= 0:
        raise SystemExit(f"Function signature is not unique: {signature_fragment}")

    open_brace = text.find("{", start)
    if open_brace < 0:
        raise SystemExit(f"Opening brace not found: {signature_fragment}")

    depth = 0
    close_brace = -1
    for index in range(open_brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                close_brace = index
                break

    if close_brace < 0:
        raise SystemExit(f"Closing brace not found: {signature_fragment}")

    text = text[:open_brace] + "{\n" + replacement_body.rstrip() + "\n}" + text[close_brace + 1:]


replace_function(
    "void SX1280Driver::startCWTest(",
    """    // RF transmit is intentionally disabled in this build.
    (void)freq;
    (void)radioNumber;
    RFAMP.TXRXdisable();
    DBGLN("RF TX disabled: continuous-wave test suppressed");"""
)

replace_function(
    "SX1280Driver::TXnb(",
    """    // Suppress every normal SX1280 packet transmission.
    // TXnbISR() advances the normal completion path and prepares telemetry RX.
    transmittingRadio = radioNumber;
    (void)data;
    (void)size;
    if (radioNumber == SX12XX_Radio_NONE)
    {
        instance->SetMode(fallBackMode, SX12XX_Radio_All);
        return;
    }
    RFAMP.TXRXdisable();
    instance->SetMode(fallBackMode, SX12XX_Radio_All);
    TXnbISR();"""
)

source.write_text(text, encoding="utf-8")
print("Patched SX1280 packet TX and continuous-wave TX.")

# ExpressLRS 3.4.2 pulls NimBLE-Arduino 2.5.1 directly, while its pinned
# ESP32-BLE-Gamepad 0.7.5 pulls NimBLE-Arduino 1.4.1 transitively.
# Gamepad 0.8.0 declares NimBLE-Arduino ^2.5.1, avoiding two copies of
# the same library being linked into the firmware.
target_config = Path("ExpressLRS/src/targets/esp32-tx.ini")
if not target_config.is_file():
    raise SystemExit(f"Expected target config not found: {target_config}")

config_text = target_config.read_text(encoding="utf-8")
pattern = re.compile(
    r"(?im)^([ \t]*[^\r\n]*ESP32-BLE-Gamepad[ \t]*@[ \t]*)0\.7\.5([ \t]*)$"
)
config_text, replacements = pattern.subn(r"\g<1>0.8.0\g<2>", config_text)
if replacements != 1:
    raise SystemExit(
        "Expected exactly one ESP32-BLE-Gamepad @ 0.7.5 dependency "
        f"in {target_config}, found {replacements}; refusing an unsafe edit."
    )

target_config.write_text(config_text, encoding="utf-8")
print("Updated ESP32-BLE-Gamepad to 0.8.0 to use the existing NimBLE-Arduino 2.5.1 dependency.")
