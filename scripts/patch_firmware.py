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

# ExpressLRS 3.4.2 keeps shared ESP32 library dependencies in
# targets/common.ini (there is no targets/esp32-tx.ini in this release).
target_config = Path("ExpressLRS/src/targets/common.ini")
if not target_config.is_file():
    raise SystemExit(f"Expected target config not found: {target_config}")

config_text = target_config.read_text(encoding="utf-8")

def replace_dependency(name: str, old_version: str, new_version: str) -> None:
    global config_text
    pattern = re.compile(
        rf"(?im)^([ \t]*[^\r\n]*{re.escape(name)}[ \t]*@[ \t]*)"
        rf"{re.escape(old_version)}([ \t]*(?:#.*)?)$"
    )
    config_text, count = pattern.subn(r"\g<1>" + new_version + r"\g<2>", config_text)
    if count != 1:
        raise SystemExit(
            f"Expected exactly one {name} @ {old_version} dependency "
            f"in {target_config}, found {count}; refusing an unsafe edit."
        )

replace_dependency("ESP32-BLE-Gamepad", "0.5.2", "0.8.0")
replace_dependency("NimBLE-Arduino", "1.4.1", "2.5.1")
target_config.write_text(config_text, encoding="utf-8")
print("Updated ESP32-BLE-Gamepad to 0.8.0 and NimBLE-Arduino to 2.5.1 in targets/common.ini.")
